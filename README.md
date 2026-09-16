# The Great Grocery Price Race — Blinkit vs Instamart

> **CarDekho Group Campus Challenge (NSUT '26)**  
> Settle the 11 PM hostel argument in one search: *"Is this cheaper on Blinkit or Instamart?"*

A lightweight, resilient web application that searches grocery listings and real-time prices across **Blinkit** and **Swiggy Instamart** for any delivery location, pairs equivalent products using intelligent fuzzy matching and pack-size verification, and highlights the cheaper option side by side.

Built adhering to **AI-DLC (AI-Driven Development Lifecycle)** standards with full test coverage, decoupled seams, and zero reverse-engineering of private mobile APIs.

---

## Key Features

- **Unified Search**: Single search input for grocery/snack items and delivery location.
- **Concurrent Scraping**: Queries Blinkit and Instamart in parallel via asynchronous Playwright headless Chromium drivers.
- **Bipartite Product Matcher**: Uses `rapidfuzz` token-set ratio combined with unit-aware normalization (`kg -> g`, `l -> ml`, `pcs`) to accurately match items and penalize pack-size mismatches.
- **Cheaper Price Highlighting**: Instantly marks the winning platform and computes exact savings, with support for price ties and stock status indicators.
- **Partial-Failure Resilience**: If one platform experiences a network timeout or anti-bot challenge, results from the other platform are still returned seamlessly.
- **In-Memory TTL Caching**: Caches search results by normalized `(query, location)` to prevent redundant requests and respect external service infrastructure.
- **100% Offline-Testable**: Decoupled HTML parser design enables full unit and integration testing against saved DOM fixtures without hitting live servers in CI.
- **Offline Demo Mode**: Supports instant, deterministic demonstration via offline fixtures for seamless screen recordings and evaluation.

---

## Quick Start (Fresh Machine Setup)

### Prerequisites
- **Python 3.11+** installed (tested on Python 3.12).
- **pip** package manager.

### 1. Clone & Set Up Environment

```bash
# Clone the repository
git clone https://github.com/Cubix33/Grocery-Price-Comparison.git
cd Grocery-Price-Comparison

# Create and activate virtual environment
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies & Playwright Browser

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Running the Application

### Option A: Standard Live Search (Default)
Starts the FastAPI server with live Playwright scrapers:

```bash
python -m app.server.main
```

Open your browser and visit: **`http://localhost:8000`**

### Option B: Offline Demo Mode (Instant Evaluation)
For grading, demonstration, or environments with restricted external internet access, run with offline fixture mode:

```bash
# On Windows (PowerShell):
$env:MOCK_SCRAPERS="1"; python -m app.server.main

# On Linux / macOS:
MOCK_SCRAPERS=1 python -m app.server.main
```

Then visit **`http://localhost:8000`** and test queries like *"Maggi"*, *"Amul Butter"*, etc.

---

## Running Automated Tests

Run the complete test suite:

```bash
pytest -v
```

All 24 unit, parser, matching, cache, and API integration tests execute offline in $<1$ second with zero external network requests:
- `tests/test_types.py`: Domain schema validation (`RawListing`, `MatchedPair`).
- `tests/matching/test_normalize.py`: Unit conversion, quantity parsing, stopword cleansing.
- `tests/matching/test_matcher.py`: Bipartite similarity pairing, pack-size mismatch penalties, tie detection.
- `tests/scrapers/blinkit/test_parse_blinkit_listings.py`: Pure DOM parsing against Blinkit HTML fixtures.
- `tests/scrapers/instamart/test_parse_instamart_listings.py`: Pure DOM parsing against Instamart HTML fixtures.
- `tests/server/test_cache.py`: Monotonic TTL eviction and query normalization.
- `tests/server/test_app.py`: FastAPI `/search` endpoint orchestration, validation, and partial failure fallbacks.

---

## Project Structure

```
Grocery-Price-Comparison/
├── aidlc-docs/                   # AI-DLC engineering audit trail & baseline specs
│   ├── inception/                # Requirements, architecture, components, stack
│   └── efforts/                  # Effort 001 state, delta, and audit logs
├── app/
│   ├── __init__.py
│   ├── types.py                  # Pydantic models (RawListing, MatchedPair)
│   ├── matching/
│   │   ├── __init__.py
│   │   ├── normalize.py          # parse_quantity(), normalize_name(), unit conversions
│   │   └── matcher.py            # match_listings() bipartite greedy matcher
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── blinkit/
│   │   │   ├── parse_blinkit_listings.py   # Pure BeautifulSoup4 HTML parser
│   │   │   └── search_blinkit.py           # Headless Playwright browser driver
│   │   └── instamart/
│   │       ├── parse_instamart_listings.py # Pure BeautifulSoup4 HTML parser
│   │       └── search_instamart.py         # Headless Playwright browser driver
│   └── server/
│       ├── __init__.py
│       ├── cache.py              # In-memory TTLCache with monotonic clock
│       ├── app.py                # FastAPI create_app factory with /search route
│       └── main.py               # Application entrypoint & static mount
├── public/                       # Zero-build static frontend
│   ├── index.html                # Responsive search layout
│   ├── styles.css                # Card grid, winner highlighting, dark theme
│   └── app.js                    # Fetch client & DOM renderer
├── tests/                        # 24-case pytest test suite
│   ├── test_types.py
│   ├── matching/
│   ├── scrapers/
│   └── server/
├── fixtures/                     # Saved HTML snapshots for deterministic testing
│   ├── blinkit_search_maggi.html
│   └── instamart_search_maggi.html
├── DESIGN_NOTE.md                # One-page architecture & failure mode design document
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## Design Note

Read [DESIGN_NOTE.md](DESIGN_NOTE.md) for the mandatory 1-page deep dive covering:
1. Architectural choices and why alternatives (raw HTTP vs Playwright, monolithic vs decoupled) were rejected.
2. Cross-platform product matching logic and honest failure modes (multipacks, private labels, variant collisions).
3. Production scaling roadmap for multi-location dark store indexing and high-concurrency scraping.

---

## Submission Details

- **Challenge**: CarDekho Group Campus Build Challenge (NSUT '26)
- **Author**: Anshika Singh ([@Cubix33](https://github.com/Cubix33))
- **Form Link**: [Submission Google Form](https://forms.gle/8HTwHLA2uHVUnfTg8)
