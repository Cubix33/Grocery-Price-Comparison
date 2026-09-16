# Grocery Price Compare Implementation Plan (Python)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Note for this session:** those two execution sub-skills aren't installed here (this is a general Claude chat/computer-use session, not a Claude Code agentic environment). The plan still follows the required format below; at the end I offer to execute it directly in this session instead.

**Goal:** Build a web app where a user enters a grocery item and a delivery location and sees matched, price-compared listings from Blinkit and Instamart in one view.

**Architecture:** Three isolated seams — a scraping layer (one Playwright-driven module per platform, each split into a pure HTML parser and a browser-driving search coroutine), a pure matching layer (normalizes names/quantities and pairs listings across platforms using rapidfuzz similarity scoring), and a thin FastAPI app + static frontend that orchestrates both scrapers concurrently, caches results, and renders paired results.

**Tech Stack:** Python 3.11+, FastAPI, Playwright (async API, Chromium), BeautifulSoup4 (HTML parsing), rapidfuzz (fuzzy string matching), pydantic (data models/validation), pytest + FastAPI's `TestClient`, vanilla HTML/CSS/JS frontend (no build step — keeps the "any stack, fresh machine" setup trivial).

**Spec:** `grocery-price-compare-spec.md` (published separately) — this plan implements every section of that spec; the spec's product-matching caveats and scope boundaries apply to every task below.

## Global Constraints

- No login flows, no mobile app, no APK reverse-engineering — desktop-site scraping only.
- Keep request volume to Blinkit/Instamart reasonable — cache results, no polling, no test suite hitting live sites.
- Do not deploy or share the running app outside this assignment.
- App must run on a fresh machine from README steps alone — no assumed global tooling beyond Python 3.11+ and pip.
- Location is set once per session and passed to both scrapers before every search.

---

## File Structure

```
grocery-price-compare/
  app/
    __init__.py
    types.py                            # RawListing, MatchedPair (pydantic models)
    matching/
      __init__.py
      normalize.py                      # normalize_name(), parse_quantity()
      matcher.py                        # match_listings()
    scrapers/
      __init__.py
      blinkit/
        __init__.py
        parse_blinkit_listings.py       # pure HTML -> RawListing[] parser
        search_blinkit.py               # Playwright driver, uses parser
      instamart/
        __init__.py
        parse_instamart_listings.py
        search_instamart.py
    server/
      __init__.py
      cache.py                          # TTLCache, cache_key()
      app.py                            # create_app(): FastAPI app factory
      main.py                           # entrypoint: wires real scrapers, mounts frontend, runs uvicorn
  public/
    index.html
    app.js
    styles.css
  tests/
    __init__.py
    matching/
      __init__.py
      test_normalize.py
      test_matcher.py
    scrapers/
      __init__.py
      blinkit/test_parse_blinkit_listings.py
      instamart/test_parse_instamart_listings.py
    server/
      __init__.py
      test_cache.py
      test_app.py
  fixtures/
    blinkit_search_maggi.html
    instamart_search_maggi.html
  requirements.txt
  pytest.ini
  README.md
```

---

### Task 1: Project scaffolding and shared types

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `app/__init__.py`, `app/types.py`
- Test: `tests/__init__.py`, `tests/test_types.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `RawListing`, `MatchedPair` pydantic models, imported by every later task

- [ ] **Step 1: Initialize the project**

```bash
mkdir grocery-price-compare && cd grocery-price-compare
python3 -m venv .venv
source .venv/bin/activate
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi
uvicorn[standard]
playwright
beautifulsoup4
rapidfuzz
pydantic
httpx
pytest
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
playwright install chromium
```

- [ ] **Step 4: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
```

- [ ] **Step 5: Create empty package markers**

```bash
mkdir -p app tests
touch app/__init__.py tests/__init__.py
```

- [ ] **Step 6: Write the failing test for shared types**

```python
# tests/test_types.py
from app.types import RawListing, MatchedPair


def test_raw_listing_and_matched_pair_hold_expected_fields():
    listing = RawListing(
        platform="blinkit",
        name="Maggi 2-Minute Noodles",
        price=14,
        quantity="140 g",
        in_stock=True,
    )

    pair = MatchedPair(blinkit=listing, instamart=None, similarity=0.0, cheaper=None)

    assert pair.blinkit.platform == "blinkit"
```

- [ ] **Step 7: Run test to verify it fails**

Run: `pytest tests/test_types.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.types'`

- [ ] **Step 8: Create `app/types.py`**

```python
from typing import Literal, Optional
from pydantic import BaseModel

Platform = Literal["blinkit", "instamart"]


class RawListing(BaseModel):
    platform: Platform
    name: str
    price: float
    quantity: str  # raw pack-size string as shown on the listing, e.g. "140 g"
    in_stock: bool
    image_url: Optional[str] = None
    url: Optional[str] = None


class MatchedPair(BaseModel):
    blinkit: Optional[RawListing] = None
    instamart: Optional[RawListing] = None
    similarity: float = 0.0
    cheaper: Optional[Literal["blinkit", "instamart", "tie"]] = None
```

- [ ] **Step 9: Run test to verify it passes**

Run: `pytest tests/test_types.py`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git init
git add .
git commit -m "chore: scaffold project and add shared types"
```

---

### Task 2: Name and quantity normalization

**Files:**
- Create: `app/matching/__init__.py`, `app/matching/normalize.py`
- Test: `tests/matching/__init__.py`, `tests/matching/test_normalize.py`

**Interfaces:**
- Consumes: nothing beyond the standard library (`re`)
- Produces: `normalize_name(raw_name: str) -> str`, `parse_quantity(text: str) -> ParsedQuantity | None` where `ParsedQuantity` has `.value: float` and `.unit: Literal["g", "ml", "pcs"]` — consumed by Task 3's matcher

- [ ] **Step 1: Write the failing tests**

```python
# tests/matching/test_normalize.py
from app.matching.normalize import normalize_name, parse_quantity


def test_parses_grams():
    result = parse_quantity("Amul Butter 500 g")
    assert result.value == 500
    assert result.unit == "g"


def test_converts_kg_to_grams():
    result = parse_quantity("Basmati Rice 1 kg")
    assert result.value == 1000
    assert result.unit == "g"


def test_converts_litres_to_ml():
    result = parse_quantity("Coca-Cola 1 L Bottle")
    assert result.value == 1000
    assert result.unit == "ml"


def test_parses_piece_counts():
    result = parse_quantity("Eggs 6 pcs")
    assert result.value == 6
    assert result.unit == "pcs"


def test_returns_none_when_no_quantity_present():
    assert parse_quantity("Assorted Snacks Combo") is None


def test_normalize_name_lowercases_strips_punctuation_and_quantity():
    assert normalize_name("Maggi 2-Minute Noodles, 140 g Pack") == "maggi 2 minute noodles"


def test_normalize_name_collapses_whitespace():
    assert normalize_name("Amul   Butter   500g") == "amul butter"


def test_normalize_name_strips_stopwords():
    assert normalize_name("Pack of Amul Butter") == "amul butter"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/matching/test_normalize.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.matching.normalize'`

- [ ] **Step 3: Implement `app/matching/normalize.py`**

```python
import re
from typing import Literal, NamedTuple, Optional

QUANTITY_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml|pcs|pc)\b", re.IGNORECASE)

UNIT_TO_BASE: dict[str, tuple[float, Literal["g", "ml", "pcs"]]] = {
    "kg": (1000, "g"),
    "g": (1, "g"),
    "l": (1000, "ml"),
    "ml": (1, "ml"),
    "pcs": (1, "pcs"),
    "pc": (1, "pcs"),
}


class ParsedQuantity(NamedTuple):
    value: float
    unit: Literal["g", "ml", "pcs"]


def parse_quantity(text: str) -> Optional[ParsedQuantity]:
    match = QUANTITY_PATTERN.search(text)
    if not match:
        return None
    raw_value = float(match.group(1))
    factor, base = UNIT_TO_BASE[match.group(2).lower()]
    return ParsedQuantity(value=raw_value * factor, unit=base)


STOPWORDS = {"the", "a", "an", "of", "with", "pack"}


def normalize_name(raw_name: str) -> str:
    without_quantity = QUANTITY_PATTERN.sub(" ", raw_name)
    lowered = without_quantity.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    tokens = [token for token in cleaned.split() if token and token not in STOPWORDS]
    return " ".join(tokens)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/matching/test_normalize.py`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add app/matching/normalize.py tests/matching/test_normalize.py
git commit -m "feat: add name/quantity normalization"
```

---

### Task 3: Cross-platform matching algorithm

**Files:**
- Create: `app/matching/matcher.py`
- Test: `tests/matching/test_matcher.py`

**Interfaces:**
- Consumes: `normalize_name`, `parse_quantity` from Task 2; `RawListing`, `MatchedPair` from Task 1; `rapidfuzz.fuzz.token_set_ratio`
- Produces: `match_listings(blinkit: list[RawListing], instamart: list[RawListing]) -> list[MatchedPair]` — consumed by Task 9's `/search` endpoint

- [ ] **Step 1: Write the failing tests**

```python
# tests/matching/test_matcher.py
from app.matching.matcher import match_listings
from app.types import RawListing


def make_listing(**overrides) -> RawListing:
    defaults = dict(
        platform="blinkit",
        name="Maggi 2-Minute Noodles 140 g",
        price=14,
        quantity="140 g",
        in_stock=True,
    )
    defaults.update(overrides)
    return RawListing(**defaults)


def test_matches_identical_products_with_same_pack_size():
    blinkit = [make_listing(platform="blinkit", price=14)]
    instamart = [make_listing(platform="instamart", price=12)]

    pairs = match_listings(blinkit, instamart)

    assert len(pairs) == 1
    assert pairs[0].blinkit is not None
    assert pairs[0].instamart is not None
    assert pairs[0].cheaper == "instamart"


def test_does_not_match_same_name_with_very_different_pack_sizes():
    blinkit = [make_listing(platform="blinkit", name="Maggi 2-Minute Noodles 70 g", quantity="70 g")]
    instamart = [
        make_listing(
            platform="instamart",
            name="Maggi 2-Minute Noodles 560 g (Family Pack)",
            quantity="560 g",
        )
    ]

    pairs = match_listings(blinkit, instamart)

    assert len(pairs) == 2
    assert all(p.blinkit is None or p.instamart is None for p in pairs)


def test_leaves_unmatched_items_from_either_platform_unpaired():
    blinkit = [make_listing(platform="blinkit", name="Amul Butter 500 g", quantity="500 g")]
    instamart = [make_listing(platform="instamart", name="Britannia Bread 400 g", quantity="400 g")]

    pairs = match_listings(blinkit, instamart)

    assert len(pairs) == 2
    blinkit_pair = next(p for p in pairs if p.blinkit is not None)
    instamart_pair = next(p for p in pairs if p.instamart is not None)
    assert blinkit_pair.instamart is None
    assert instamart_pair.blinkit is None


def test_picks_the_best_of_several_candidates_on_the_other_platform():
    blinkit = [make_listing(platform="blinkit", name="Amul Butter 500 g", quantity="500 g")]
    instamart = [
        make_listing(platform="instamart", name="Amul Cheese 500 g", quantity="500 g"),
        make_listing(platform="instamart", name="Amul Butter 500 g", quantity="500 g"),
    ]

    pairs = match_listings(blinkit, instamart)
    matched = next(p for p in pairs if p.blinkit is not None and p.instamart is not None)

    assert matched.instamart.name == "Amul Butter 500 g"


def test_reports_a_tie_when_prices_are_equal():
    blinkit = [make_listing(platform="blinkit", price=20)]
    instamart = [make_listing(platform="instamart", price=20)]

    pairs = match_listings(blinkit, instamart)

    assert pairs[0].cheaper == "tie"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/matching/test_matcher.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.matching.matcher'`

- [ ] **Step 3: Implement `app/matching/matcher.py`**

```python
from rapidfuzz import fuzz

from app.matching.normalize import normalize_name, parse_quantity
from app.types import MatchedPair, RawListing

NAME_MATCH_THRESHOLD = 55.0  # rapidfuzz token_set_ratio is 0-100
QUANTITY_MATCH_TOLERANCE = 0.1  # 10%
QUANTITY_MATCH_BONUS = 15.0
QUANTITY_MISMATCH_PENALTY = 15.0


def _pick_cheaper(a: RawListing, b: RawListing) -> str:
    if a.price == b.price:
        return "tie"
    return a.platform if a.price < b.price else b.platform


def match_listings(blinkit_listings: list[RawListing], instamart_listings: list[RawListing]) -> list[MatchedPair]:
    pairs: list[MatchedPair] = []
    used_instamart: set[int] = set()

    for blinkit_item in blinkit_listings:
        blinkit_norm = normalize_name(blinkit_item.name)
        blinkit_qty = parse_quantity(blinkit_item.name) or parse_quantity(blinkit_item.quantity)

        best_index = -1
        best_score = 0.0

        for index, instamart_item in enumerate(instamart_listings):
            if index in used_instamart:
                continue

            instamart_norm = normalize_name(instamart_item.name)
            score = fuzz.token_set_ratio(blinkit_norm, instamart_norm)

            instamart_qty = parse_quantity(instamart_item.name) or parse_quantity(instamart_item.quantity)
            if blinkit_qty and instamart_qty and blinkit_qty.unit == instamart_qty.unit:
                diff = abs(blinkit_qty.value - instamart_qty.value) / blinkit_qty.value
                score += QUANTITY_MATCH_BONUS if diff <= QUANTITY_MATCH_TOLERANCE else -QUANTITY_MISMATCH_PENALTY

            if score > best_score:
                best_score = score
                best_index = index

        if best_index >= 0 and best_score >= NAME_MATCH_THRESHOLD:
            used_instamart.add(best_index)
            instamart_item = instamart_listings[best_index]
            pairs.append(
                MatchedPair(
                    blinkit=blinkit_item,
                    instamart=instamart_item,
                    similarity=min(best_score, 100.0) / 100.0,
                    cheaper=_pick_cheaper(blinkit_item, instamart_item),
                )
            )
        else:
            pairs.append(MatchedPair(blinkit=blinkit_item, instamart=None, similarity=0.0, cheaper=None))

    for index, item in enumerate(instamart_listings):
        if index not in used_instamart:
            pairs.append(MatchedPair(blinkit=None, instamart=item, similarity=0.0, cheaper=None))

    return pairs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/matching/test_matcher.py`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add app/matching/matcher.py tests/matching/test_matcher.py
git commit -m "feat: add cross-platform listing matcher using rapidfuzz"
```

---

### Task 4: Blinkit HTML parser

**Files:**
- Create: `app/scrapers/__init__.py`, `app/scrapers/blinkit/__init__.py`, `app/scrapers/blinkit/parse_blinkit_listings.py`
- Create: `fixtures/blinkit_search_maggi.html`
- Test: `tests/scrapers/__init__.py`, `tests/scrapers/blinkit/test_parse_blinkit_listings.py`

**Interfaces:**
- Consumes: `RawListing` from Task 1
- Produces: `parse_blinkit_listings(html: str) -> list[RawListing]` — consumed by Task 5's `search_blinkit`

**Note:** the selectors below (`.ProductCard`, `.ProductCard__name`, etc.) are a documented placeholder for Blinkit's actual current DOM structure, which can only be confirmed by opening the live site in a browser and inspecting it — it is not knowable offline and changes over time. The concrete action item is: **before wiring this into Task 5, open blinkit.com in a browser, search for an item, and use DevTools to update the selector constants at the top of this file to match the real markup.** The parser logic, fixture, and tests below are written against a fixture using these placeholder selectors so the parsing logic itself is fully tested now; only the selector strings need updating later.

- [ ] **Step 1: Create the fixture**

```html
<!-- fixtures/blinkit_search_maggi.html -->
<html>
  <body>
    <div class="ProductCard">
      <div class="ProductCard__name">Maggi 2-Minute Noodles</div>
      <div class="ProductCard__quantity">140 g</div>
      <div class="ProductCard__price">₹14</div>
      <div class="ProductCard__stock">In stock</div>
    </div>
    <div class="ProductCard">
      <div class="ProductCard__name">Maggi 2-Minute Noodles (Family Pack)</div>
      <div class="ProductCard__quantity">560 g</div>
      <div class="ProductCard__price">₹56</div>
      <div class="ProductCard__stock">Out of stock</div>
    </div>
  </body>
</html>
```

- [ ] **Step 2: Write the failing test**

```python
# tests/scrapers/blinkit/test_parse_blinkit_listings.py
from pathlib import Path

from app.scrapers.blinkit.parse_blinkit_listings import parse_blinkit_listings

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "blinkit_search_maggi.html"


def test_parses_listings_from_a_saved_blinkit_search_results_page():
    html = FIXTURE.read_text(encoding="utf-8")

    listings = parse_blinkit_listings(html)

    assert len(listings) == 2
    assert listings[0].platform == "blinkit"
    assert listings[0].name == "Maggi 2-Minute Noodles"
    assert listings[0].price == 14
    assert listings[0].quantity == "140 g"
    assert listings[0].in_stock is True
    assert listings[1].in_stock is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/scrapers/blinkit/test_parse_blinkit_listings.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.scrapers.blinkit.parse_blinkit_listings'`

- [ ] **Step 4: Implement the parser**

```python
# app/scrapers/blinkit/parse_blinkit_listings.py
from bs4 import BeautifulSoup

from app.types import RawListing

# TODO-AT-IMPLEMENTATION-TIME: confirm against the live site's current DOM.
SELECTORS = {
    "card": ".ProductCard",
    "name": ".ProductCard__name",
    "quantity": ".ProductCard__quantity",
    "price": ".ProductCard__price",
    "stock": ".ProductCard__stock",
}


def parse_blinkit_listings(html: str) -> list[RawListing]:
    soup = BeautifulSoup(html, "html.parser")
    listings: list[RawListing] = []

    for card in soup.select(SELECTORS["card"]):
        name_el = card.select_one(SELECTORS["name"])
        quantity_el = card.select_one(SELECTORS["quantity"])
        price_el = card.select_one(SELECTORS["price"])
        stock_el = card.select_one(SELECTORS["stock"])

        name = name_el.get_text(strip=True) if name_el else ""
        quantity = quantity_el.get_text(strip=True) if quantity_el else ""
        price_text = price_el.get_text(strip=True) if price_el else ""
        stock_text = (stock_el.get_text(strip=True) if stock_el else "").lower()

        price_digits = "".join(ch for ch in price_text if ch.isdigit() or ch == ".")
        if not name or not price_digits:
            continue

        listings.append(
            RawListing(
                platform="blinkit",
                name=name,
                price=float(price_digits),
                quantity=quantity,
                in_stock="out of stock" not in stock_text,
            )
        )

    return listings
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/scrapers/blinkit/test_parse_blinkit_listings.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/scrapers/blinkit/parse_blinkit_listings.py fixtures/blinkit_search_maggi.html tests/scrapers/blinkit/test_parse_blinkit_listings.py
git commit -m "feat: add Blinkit listings HTML parser"
```

---

### Task 5: Blinkit live search driver (Playwright)

**Files:**
- Create: `app/scrapers/blinkit/search_blinkit.py`

**Interfaces:**
- Consumes: `parse_blinkit_listings` from Task 4
- Produces: `async def search_blinkit(query: str, location: str) -> list[RawListing]` — consumed by Task 11's entrypoint

This task drives a real browser against the live site, so it is not unit-testable the way Tasks 2–4 are (no fixture stands in for real navigation, and the plan explicitly avoids hitting the live site in the automated test suite to keep request volume reasonable — see Global Constraints). It is verified by manual smoke test instead.

- [ ] **Step 1: Implement the driver**

```python
# app/scrapers/blinkit/search_blinkit.py
from playwright.async_api import async_playwright

from app.scrapers.blinkit.parse_blinkit_listings import parse_blinkit_listings
from app.types import RawListing

# TODO-AT-IMPLEMENTATION-TIME: confirm these against the live site.
HOME_URL = "https://blinkit.com/"
SELECTORS = {
    "location_input": '[data-testid="location-search-input"]',
    "location_suggestion": '[data-testid="location-suggestion"]:first-child',
    "search_input": '[data-testid="search-input"]',
}


async def search_blinkit(query: str, location: str) -> list[RawListing]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(HOME_URL, wait_until="networkidle")

            await page.click(SELECTORS["location_input"])
            await page.fill(SELECTORS["location_input"], location)
            await page.click(SELECTORS["location_suggestion"])

            await page.click(SELECTORS["search_input"])
            await page.fill(SELECTORS["search_input"], query)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")

            html = await page.content()
            return parse_blinkit_listings(html)
        finally:
            await browser.close()
```

- [ ] **Step 2: Manual smoke test**

Run:
```bash
python -c "
import asyncio
from app.scrapers.blinkit.search_blinkit import search_blinkit

async def main():
    results = await search_blinkit('Maggi', 'your test address here')
    for r in results:
        print(r)

asyncio.run(main())
"
```
Expected: printed listings with real names/prices from Blinkit; an empty result means the DevTools inspection from Task 4's note was skipped or the selectors have changed — re-inspect and update `SELECTORS`/`HOME_URL`.

- [ ] **Step 3: Commit**

```bash
git add app/scrapers/blinkit/search_blinkit.py
git commit -m "feat: add Blinkit live search driver"
```

---

### Task 6: Instamart HTML parser

**Files:**
- Create: `app/scrapers/instamart/__init__.py`, `app/scrapers/instamart/parse_instamart_listings.py`
- Create: `fixtures/instamart_search_maggi.html`
- Test: `tests/scrapers/instamart/test_parse_instamart_listings.py`

**Interfaces:**
- Consumes: `RawListing` from Task 1
- Produces: `parse_instamart_listings(html: str) -> list[RawListing]` — consumed by Task 7's `search_instamart`

Same caveat as Task 4: selectors are placeholders to be confirmed against the live site before Task 7 is wired up for real use.

- [ ] **Step 1: Create the fixture**

```html
<!-- fixtures/instamart_search_maggi.html -->
<html>
  <body>
    <div class="item-widget-container">
      <div class="item-name">Maggi 2-Minute Noodles</div>
      <div class="item-quantity">140 g</div>
      <div class="item-price">Rs. 12</div>
      <div class="item-availability">Available</div>
    </div>
    <div class="item-widget-container">
      <div class="item-name">Maggi Masala Noodles Family Pack</div>
      <div class="item-quantity">560 g</div>
      <div class="item-price">Rs. 54</div>
      <div class="item-availability">Sold Out</div>
    </div>
  </body>
</html>
```

- [ ] **Step 2: Write the failing test**

```python
# tests/scrapers/instamart/test_parse_instamart_listings.py
from pathlib import Path

from app.scrapers.instamart.parse_instamart_listings import parse_instamart_listings

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "instamart_search_maggi.html"


def test_parses_listings_from_a_saved_instamart_search_results_page():
    html = FIXTURE.read_text(encoding="utf-8")

    listings = parse_instamart_listings(html)

    assert len(listings) == 2
    assert listings[0].platform == "instamart"
    assert listings[0].name == "Maggi 2-Minute Noodles"
    assert listings[0].price == 12
    assert listings[0].quantity == "140 g"
    assert listings[0].in_stock is True
    assert listings[1].in_stock is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/scrapers/instamart/test_parse_instamart_listings.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.scrapers.instamart.parse_instamart_listings'`

- [ ] **Step 4: Implement the parser**

```python
# app/scrapers/instamart/parse_instamart_listings.py
from bs4 import BeautifulSoup

from app.types import RawListing

# TODO-AT-IMPLEMENTATION-TIME: confirm against the live site's current DOM.
SELECTORS = {
    "card": ".item-widget-container",
    "name": ".item-name",
    "quantity": ".item-quantity",
    "price": ".item-price",
    "stock": ".item-availability",
}


def parse_instamart_listings(html: str) -> list[RawListing]:
    soup = BeautifulSoup(html, "html.parser")
    listings: list[RawListing] = []

    for card in soup.select(SELECTORS["card"]):
        name_el = card.select_one(SELECTORS["name"])
        quantity_el = card.select_one(SELECTORS["quantity"])
        price_el = card.select_one(SELECTORS["price"])
        stock_el = card.select_one(SELECTORS["stock"])

        name = name_el.get_text(strip=True) if name_el else ""
        quantity = quantity_el.get_text(strip=True) if quantity_el else ""
        price_text = price_el.get_text(strip=True) if price_el else ""
        stock_text = (stock_el.get_text(strip=True) if stock_el else "").lower()

        price_digits = "".join(ch for ch in price_text if ch.isdigit() or ch == ".")
        if not name or not price_digits:
            continue

        listings.append(
            RawListing(
                platform="instamart",
                name=name,
                price=float(price_digits),
                quantity=quantity,
                in_stock="sold out" not in stock_text,
            )
        )

    return listings
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/scrapers/instamart/test_parse_instamart_listings.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/scrapers/instamart/parse_instamart_listings.py fixtures/instamart_search_maggi.html tests/scrapers/instamart/test_parse_instamart_listings.py
git commit -m "feat: add Instamart listings HTML parser"
```

---

### Task 7: Instamart live search driver (Playwright)

**Files:**
- Create: `app/scrapers/instamart/search_instamart.py`

**Interfaces:**
- Consumes: `parse_instamart_listings` from Task 6
- Produces: `async def search_instamart(query: str, location: str) -> list[RawListing]` — consumed by Task 11's entrypoint

Same non-unit-testable nature as Task 5; verified by manual smoke test.

- [ ] **Step 1: Implement the driver**

```python
# app/scrapers/instamart/search_instamart.py
from playwright.async_api import async_playwright

from app.scrapers.instamart.parse_instamart_listings import parse_instamart_listings
from app.types import RawListing

# TODO-AT-IMPLEMENTATION-TIME: confirm these against the live site.
HOME_URL = "https://www.swiggy.com/instamart"
SELECTORS = {
    "location_input": '[data-testid="location-input"]',
    "location_suggestion": '[data-testid="location-suggestion"]:first-child',
    "search_input": '[data-testid="instamart-search-input"]',
}


async def search_instamart(query: str, location: str) -> list[RawListing]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(HOME_URL, wait_until="networkidle")

            await page.click(SELECTORS["location_input"])
            await page.fill(SELECTORS["location_input"], location)
            await page.click(SELECTORS["location_suggestion"])

            await page.click(SELECTORS["search_input"])
            await page.fill(SELECTORS["search_input"], query)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")

            html = await page.content()
            return parse_instamart_listings(html)
        finally:
            await browser.close()
```

- [ ] **Step 2: Manual smoke test**

Run:
```bash
python -c "
import asyncio
from app.scrapers.instamart.search_instamart import search_instamart

async def main():
    results = await search_instamart('Maggi', 'your test address here')
    for r in results:
        print(r)

asyncio.run(main())
"
```
Expected: printed listings with real names/prices; empty results mean the selectors need re-confirming against the live DOM, as noted in Task 6.

- [ ] **Step 3: Commit**

```bash
git add app/scrapers/instamart/search_instamart.py
git commit -m "feat: add Instamart live search driver"
```

---

### Task 8: TTL cache

**Files:**
- Create: `app/server/__init__.py`, `app/server/cache.py`
- Test: `tests/server/__init__.py`, `tests/server/test_cache.py`

**Interfaces:**
- Consumes: standard library `time`
- Produces: `TTLCache[T]` class (`.get`, `.set`), `cache_key(query: str, location: str) -> str` — consumed by Task 9's `create_app`

- [ ] **Step 1: Write the failing tests**

```python
# tests/server/test_cache.py
from app.server.cache import TTLCache, cache_key
import app.server.cache as cache_module


def test_cache_key_normalizes_case_and_whitespace():
    assert cache_key("Maggi", " Hostel Block A ") == cache_key("maggi", "hostel block a")


def test_returns_a_stored_value_before_it_expires():
    cache: TTLCache[str] = TTLCache(ttl_seconds=1000)
    cache.set("key", "value")
    assert cache.get("key") == "value"


def test_returns_none_after_ttl_elapses(monkeypatch):
    fake_time = {"now": 1000.0}
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: fake_time["now"])

    cache: TTLCache[str] = TTLCache(ttl_seconds=1.0)
    cache.set("key", "value")

    fake_time["now"] += 1.001

    assert cache.get("key") is None


def test_returns_none_for_a_key_that_was_never_set():
    cache: TTLCache[str] = TTLCache(ttl_seconds=1000)
    assert cache.get("missing") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/server/test_cache.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.server.cache'`

- [ ] **Step 3: Implement `app/server/cache.py`**

```python
import time
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class _CacheEntry(Generic[T]):
    def __init__(self, value: T, expires_at: float):
        self.value = value
        self.expires_at = expires_at


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float):
        self._ttl_seconds = ttl_seconds
        self._store: dict[str, _CacheEntry[T]] = {}

    def get(self, key: str) -> Optional[T]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._store[key] = _CacheEntry(value, time.monotonic() + self._ttl_seconds)


def cache_key(query: str, location: str) -> str:
    return f"{query.strip().lower()}::{location.strip().lower()}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/server/test_cache.py`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/server/cache.py tests/server/test_cache.py
git commit -m "feat: add TTL cache for search results"
```

---

### Task 9: `/search` API endpoint

**Files:**
- Create: `app/server/app.py`
- Test: `tests/server/test_app.py`

**Interfaces:**
- Consumes: `match_listings` (Task 3), `TTLCache`/`cache_key` (Task 8), `RawListing` (Task 1)
- Produces: `create_app(search_blinkit: SearchFn, search_instamart: SearchFn, cache: TTLCache | None = None) -> FastAPI` where `SearchFn = Callable[[str, str], Awaitable[list[RawListing]]]` — consumed by Task 11's entrypoint and Task 10's frontend (via `GET /search?q=&location=`)

Deliberately does **not** mount the `public/` frontend directory — that directory doesn't exist until Task 10, and FastAPI's `StaticFiles` raises at construction time if its directory is missing, which would break this task's tests. Static mounting is Task 11's responsibility, kept separate from the API app factory so this task's tests never touch the filesystem beyond what pytest itself needs.

- [ ] **Step 1: Write the failing tests**

```python
# tests/server/test_app.py
from fastapi.testclient import TestClient

from app.server.app import create_app
from app.types import RawListing

MAGGI_BLINKIT = RawListing(
    platform="blinkit", name="Maggi 2-Minute Noodles 140 g", price=14, quantity="140 g", in_stock=True
)
MAGGI_INSTAMART = RawListing(
    platform="instamart", name="Maggi 2-Minute Noodles 140 g", price=12, quantity="140 g", in_stock=True
)


async def fake_blinkit(query: str, location: str) -> list[RawListing]:
    return [MAGGI_BLINKIT]


async def fake_instamart(query: str, location: str) -> list[RawListing]:
    return [MAGGI_INSTAMART]


def test_returns_matched_results_for_a_valid_query_and_location():
    app = create_app(fake_blinkit, fake_instamart)
    client = TestClient(app)

    res = client.get("/search", params={"q": "Maggi", "location": "Hostel Block A"})

    assert res.status_code == 200
    body = res.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["cheaper"] == "instamart"


def test_rejects_a_request_missing_query_or_location():
    app = create_app(fake_blinkit, fake_instamart)
    client = TestClient(app)

    res = client.get("/search", params={"q": "Maggi"})

    assert res.status_code == 400


def test_still_returns_the_working_platform_if_the_other_fails():
    async def failing_instamart(query: str, location: str) -> list[RawListing]:
        raise RuntimeError("Instamart unreachable")

    app = create_app(fake_blinkit, failing_instamart)
    client = TestClient(app)

    res = client.get("/search", params={"q": "Maggi", "location": "Hostel Block A"})

    assert res.status_code == 200
    body = res.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["blinkit"] is not None
    assert body["results"][0]["instamart"] is None


def test_serves_repeated_identical_queries_from_cache():
    call_count = {"n": 0}

    async def counting_blinkit(query: str, location: str) -> list[RawListing]:
        call_count["n"] += 1
        return [MAGGI_BLINKIT]

    app = create_app(counting_blinkit, fake_instamart)
    client = TestClient(app)

    client.get("/search", params={"q": "Maggi", "location": "Hostel Block A"})
    client.get("/search", params={"q": "maggi", "location": "hostel block a"})

    assert call_count["n"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/server/test_app.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.server.app'`

- [ ] **Step 3: Implement `app/server/app.py`**

```python
import asyncio
from typing import Awaitable, Callable, Optional

from fastapi import FastAPI, HTTPException, Query

from app.matching.matcher import match_listings
from app.server.cache import TTLCache, cache_key
from app.types import RawListing

SearchFn = Callable[[str, str], Awaitable[list[RawListing]]]


class CachedResult:
    def __init__(self, blinkit: list[RawListing], instamart: list[RawListing]):
        self.blinkit = blinkit
        self.instamart = instamart


def create_app(
    search_blinkit: SearchFn,
    search_instamart: SearchFn,
    cache: Optional[TTLCache[CachedResult]] = None,
) -> FastAPI:
    cache = cache or TTLCache[CachedResult](ttl_seconds=300)
    app = FastAPI()

    @app.get("/search")
    async def search(q: str = Query(default=""), location: str = Query(default="")):
        query = q.strip()
        loc = location.strip()

        if not query or not loc:
            raise HTTPException(status_code=400, detail="q and location are both required")

        key = cache_key(query, loc)
        cached = cache.get(key)

        if cached is None:
            blinkit_result, instamart_result = await asyncio.gather(
                search_blinkit(query, loc), search_instamart(query, loc), return_exceptions=True
            )
            blinkit_listings = blinkit_result if isinstance(blinkit_result, list) else []
            instamart_listings = instamart_result if isinstance(instamart_result, list) else []
            cached = CachedResult(blinkit_listings, instamart_listings)
            cache.set(key, cached)

        results = match_listings(cached.blinkit, cached.instamart)
        return {"query": query, "location": loc, "results": [r.model_dump() for r in results]}

    return app
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/server/test_app.py`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/server/app.py tests/server/test_app.py
git commit -m "feat: add /search API endpoint with caching and partial-failure handling"
```

---

### Task 10: Frontend

**Files:**
- Create: `public/index.html`
- Create: `public/app.js`
- Create: `public/styles.css`

**Interfaces:**
- Consumes: `GET /search?q=&location=` from Task 9, response shape `{ query, location, results: MatchedPair[] }` — field names match pydantic's default `model_dump()` output (`blinkit`, `instamart`, `similarity`, `cheaper`, and on each listing `platform`, `name`, `price`, `quantity`, `in_stock`, `image_url`, `url`)
- Produces: static assets consumed by Task 11's mount — final UI layer, nothing else consumes it

No automated test framework is added for the frontend — the assignment is explicit that UI polish isn't graded, and DOM/browser testing would add setup weight disproportionate to the deliverable. Verified with the manual steps at the end of this task instead.

- [ ] **Step 1: Implement `public/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Grocery Price Compare</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <main>
    <h1>Grocery Price Compare</h1>
    <form id="search-form">
      <input id="location-input" type="text" placeholder="Delivery location (e.g. Hostel Block A, Delhi)" required />
      <input id="query-input" type="text" placeholder="Search for an item (e.g. Maggi)" required />
      <button type="submit">Compare prices</button>
    </form>
    <p id="status"></p>
    <div id="results"></div>
  </main>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Implement `public/app.js`**

```javascript
const form = document.getElementById('search-form');
const statusEl = document.getElementById('status');
const resultsEl = document.getElementById('results');

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  const query = document.getElementById('query-input').value.trim();
  const location = document.getElementById('location-input').value.trim();

  resultsEl.innerHTML = '';
  statusEl.textContent = 'Searching Blinkit and Instamart…';

  try {
    const res = await fetch(`/search?q=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}`);
    const data = await res.json();

    if (!res.ok) {
      statusEl.textContent = data.detail || 'Something went wrong.';
      return;
    }

    if (data.results.length === 0) {
      statusEl.textContent = 'No matching listings found on either platform.';
      return;
    }

    statusEl.textContent = `${data.results.length} result(s) for "${data.query}" delivered to "${data.location}"`;
    renderResults(data.results);
  } catch (err) {
    statusEl.textContent = 'Could not reach the server. Is it running?';
  }
});

function renderResults(pairs) {
  for (const pair of pairs) {
    const card = document.createElement('div');
    card.className = 'result-card';

    card.appendChild(renderListingColumn('Blinkit', pair.blinkit, pair.cheaper === 'blinkit'));
    card.appendChild(renderListingColumn('Instamart', pair.instamart, pair.cheaper === 'instamart'));

    resultsEl.appendChild(card);
  }
}

function renderListingColumn(platformLabel, listing, isCheaper) {
  const column = document.createElement('div');
  column.className = 'listing-column' + (isCheaper ? ' cheaper' : '');

  if (!listing) {
    column.innerHTML = `<h3>${platformLabel}</h3><p class="no-match">No matching listing found</p>`;
    return column;
  }

  column.innerHTML = `
    <h3>${platformLabel}${isCheaper ? ' — cheaper' : ''}</h3>
    <p class="name">${listing.name}</p>
    <p class="quantity">${listing.quantity}</p>
    <p class="price">₹${listing.price}</p>
    <p class="stock">${listing.in_stock ? 'In stock' : 'Out of stock'}</p>
  `;
  return column;
}
```

- [ ] **Step 3: Implement `public/styles.css`**

```css
body {
  font-family: system-ui, sans-serif;
  max-width: 700px;
  margin: 2rem auto;
  padding: 0 1rem;
}

#search-form {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

#search-form input {
  flex: 1;
  padding: 0.5rem;
}

.result-card {
  display: flex;
  gap: 1rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.listing-column {
  flex: 1;
  padding: 0.5rem;
}

.listing-column.cheaper {
  background: #e6f7e9;
  border-radius: 6px;
}

.no-match {
  color: #999;
  font-style: italic;
}
```

- [ ] **Step 4: Commit**

```bash
git add public/
git commit -m "feat: add frontend search UI"
```

(Manual verification of the rendered UI happens in Task 11, once it's actually being served.)

---

### Task 11: Server entrypoint (wire it all together)

**Files:**
- Create: `app/server/main.py`

**Interfaces:**
- Consumes: `create_app` (Task 9), `search_blinkit` (Task 5), `search_instamart` (Task 7), `public/` (Task 10)
- Produces: the running application — final task, nothing downstream

- [ ] **Step 1: Implement `app/server/main.py`**

```python
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles

from app.scrapers.blinkit.search_blinkit import search_blinkit
from app.scrapers.instamart.search_instamart import search_instamart
from app.server.app import create_app

PUBLIC_DIR = Path(__file__).resolve().parents[2] / "public"

app = create_app(search_blinkit, search_instamart)
app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 2: End-to-end manual smoke test**

Run: `python -m app.server.main`, open `http://localhost:8000`, search "Maggi" with a real deliverable address, confirm both platforms' listings appear (or the one working platform, per Task 9's partial-failure handling, if a selector needs re-confirming per Tasks 4–7's notes) and the cheaper column is highlighted.

- [ ] **Step 3: Commit**

```bash
git add app/server/main.py
git commit -m "feat: wire scrapers and static frontend into the running server"
```

---

### Task 12: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write setup and run instructions**

```markdown
# Grocery Price Compare

Compares grocery prices between Blinkit and Instamart for a single search query and delivery location.

## Setup (fresh machine)

1. Install Python 3.11+.
2. `python3 -m venv .venv && source .venv/bin/activate` (on Windows: `.venv\Scripts\activate`)
3. `pip install -r requirements.txt`
4. `playwright install chromium` (downloads the browser Playwright automates)

## Run

```bash
python -m app.server.main
```

Then open http://localhost:8000, enter a delivery location and a grocery item, and submit.

## Test

```bash
pytest
```

Runs the full unit/integration suite (normalization, matching, HTML parsers against saved fixtures, cache, API). No network calls are made during tests, in line with the assignment's "keep request volume reasonable" ground rule — the two Playwright-driven scraper coroutines are exercised only via the manual smoke tests described in the implementation plan, not in CI.

## Known limitations

See the one-page design note for the full discussion of where cross-platform product matching breaks down (private-label items, multipacks vs singles, near-duplicate flavor variants) and what would change to support multiple locations or many concurrent users.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and run steps"
```

---

## Self-Review

**1. Spec coverage:**
- Single search box + one-time location, results from both platforms → Tasks 9, 10.
- "Same product" matching + documented failure modes → Task 3 (algorithm, now backed by rapidfuzz instead of a hand-rolled coefficient), design note (failure modes — a writing task, not a code task, so out of scope of this plan).
- Partial-platform-failure handling → Task 9, Step 3 test.
- No-results state → Task 10, `app.js` status message.
- Reasonable request volume → Task 8 cache + README note that tests never hit live sites.
- README with fresh-machine setup → Task 12.
- No login/mobile/APK, desktop-site only → reflected in Global Constraints; no task introduces any of these.
- Gap found and fixed during review: `create_app` originally mounted `StaticFiles` directly, which would have made Task 9's tests fail before Task 10's `public/` directory existed (`StaticFiles` raises at construction time if the directory is missing) — moved static mounting out of `create_app` and into Task 11's `main.py`, keeping the API app factory filesystem-independent.

**2. Placeholder scan:** The `TODO-AT-IMPLEMENTATION-TIME` comments in Tasks 4–7 are intentional and explicit (real, current DOM selectors cannot be determined without a live browser session against sites that change their markup over time) — each is paired with a concrete verification step (DevTools inspection, manual smoke test), not a vague deferral. No other placeholders, "TBD"s, or "handle edge cases" steps remain.

**3. Type consistency:** `RawListing` (Task 1) is used identically by both parsers (Tasks 4, 6), both drivers (Tasks 5, 7), the matcher (Task 3), and the API (Task 9). `MatchedPair` (Task 1) is produced only by `match_listings` (Task 3) and consumed only by the `/search` response's `model_dump()` (Task 9) and the frontend's `renderResults` (Task 10) — field names (`blinkit`, `instamart`, `similarity`, `cheaper`, and pydantic's `in_stock` snake_case) match across all three; `app.js` reads `listing.in_stock` to match pydantic's default serialization rather than the `inStock` camelCase used in the TypeScript version of this plan.

---

**Plan complete and saved to `docs/superpowers/plans/2026-09-16-grocery-price-compare-python.md`.**

This session doesn't have the `superpowers:subagent-driven-development` or `superpowers:executing-plans` sub-skills installed (no Claude Code agentic tooling here), so the usual two-option handoff doesn't apply as-is. Instead:

1. **I execute it directly in this chat**, task by task, running the actual commands and showing you the code and test output as I go.
2. **You take the plan and run it yourself** (e.g. in Claude Code, where those sub-skills would be available) — the file is saved and ready to hand off.

Which would you like?