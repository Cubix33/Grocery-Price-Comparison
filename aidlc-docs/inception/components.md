# Baseline Component Breakdown

## 1. Domain Types (`app.types`)
- `Platform`: Literal `["blinkit", "instamart"]`.
- `RawListing`: Pydantic model capturing `platform`, `name`, `price`, `quantity`, `in_stock`, `image_url`, `url`.
- `MatchedPair`: Pydantic model capturing `blinkit`, `instamart`, `similarity` ($0.0 \dots 1.0$), and `cheaper` (`"blinkit" | "instamart" | "tie" | None`).

## 2. Normalization & Matching (`app.matching`)
- `normalize.py`:
  - `parse_quantity(text: str) -> Optional[ParsedQuantity]`: Extracts numeric quantities and converts units to standard canonical metrics (`kg -> g`, `l -> ml`).
  - `normalize_name(raw_name: str) -> str`: Normalizes strings, strips quantities, cleans punctuation, and removes domain stopwords (`the`, `a`, `an`, `of`, `with`, `pack`).
- `matcher.py`:
  - `match_listings(blinkit: list[RawListing], instamart: list[RawListing]) -> list[MatchedPair]`: Greedy bipartite matching algorithm finding optimal candidate pairs above similarity threshold (55.0 base).

## 3. Web Scraping Engine (`app.scrapers`)
- `blinkit/`:
  - `parse_blinkit_listings.py`: Pure BeautifulSoup4 DOM parser converting raw Blinkit HTML into `list[RawListing]`.
  - `search_blinkit.py`: Playwright coroutine managing headless Chromium, location selection, query execution, and DOM extraction.
- `instamart/`:
  - `parse_instamart_listings.py`: Pure BeautifulSoup4 DOM parser converting raw Instamart HTML into `list[RawListing]`.
  - `search_instamart.py`: Playwright coroutine managing headless Chromium, location selection, query execution, and DOM extraction.

## 4. API & Caching (`app.server`)
- `cache.py`: `TTLCache[T]` with monotonic time expiration and `cache_key(query, location)` normalization.
- `app.py`: `create_app(search_blinkit, search_instamart, cache)` parameterized factory enabling fast, deterministic dependency injection during testing.
- `main.py`: Entrypoint assembling real scrapers, mounting static frontend assets, and launching Uvicorn ASGI server.

## 5. Web Interface (`public/`)
- `index.html`: Responsive search layout with location and item inputs.
- `styles.css`: Clean grid/card presentation with highlighted cheaper platform badges.
- `app.js`: Asynchronous fetch handler rendering paired cards, loading indicators, and error banners.
