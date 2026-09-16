# Baseline Architecture: Modular 3-Seam Design

```
+-------------------------------------------------------------+
|                      Browser / Client                       |
|               (Vanilla HTML5 / CSS3 / ES6)                  |
+-------------------------------------------------------------+
                              |
                              | HTTP GET /search?q=...&location=...
                              v
+-------------------------------------------------------------+
|                     FastAPI Backend                         |
|   +-----------------------------------------------------+   |
|   |                  TTL Query Cache                    |   |
|   +-----------------------------------------------------+   |
|                              |                              |
|                              v                              |
|             asyncio.gather (Concurrent Scraping)            |
|               /                              \              |
|              v                                v             |
|   +--------------------+            +--------------------+  |
|   |   Blinkit Driver   |            |  Instamart Driver  |  |
|   |    (Playwright)    |            |    (Playwright)    |  |
|   +--------------------+            +--------------------+  |
|              |                                |             |
|              v                                v             |
|   +--------------------+            +--------------------+  |
|   |  Blinkit Parser    |            |  Instamart Parser  |  |
|   | (BeautifulSoup4)   |            | (BeautifulSoup4)   |  |
|   +--------------------+            +--------------------+  |
|               \                              /              |
|                +--------------+-------------+               |
|                               |                             |
|                               v                             |
|               +-------------------------------+             |
|               |       Matching Engine         |             |
|               |  (rapidfuzz + unit normalize) |             |
|               +-------------------------------+             |
|                               |                             |
+-------------------------------------------------------------+
```

## Architectural Seams

### 1. Fetch & Scraping Layer
- **Interface**: `SearchFn = Callable[[str, str], Awaitable[list[RawListing]]]`
- **Decoupling**: Each platform scraper is subdivided into:
  - An asynchronous Playwright driver handling browser lifecycle, location setting, and page navigation.
  - A pure, offline-testable HTML parser utilizing BeautifulSoup4 against DOM snapshots.
- **Fault Tolerance**: Network failures or DOM shifts on one platform are trapped via `asyncio.gather(..., return_exceptions=True)`, allowing partial result delivery.

### 2. Matching & Normalization Layer
- **Interface**: `match_listings(blinkit: list[RawListing], instamart: list[RawListing]) -> list[MatchedPair]`
- **Design**: Pure mathematical / heuristic function with zero I/O side-effects.
- **Normalization Pipeline**:
  1. Unit and quantity extraction via regex (`kg`, `g`, `l`, `ml`, `pcs`, `pc`) converting to canonical base units (`g`, `ml`, `pcs`).
  2. Stopword elimination and alphanumeric tokenization.
  3. Token-set ratio fuzzy scoring (`rapidfuzz.fuzz.token_set_ratio`).
  4. Unit-aware tolerance adjustment: $+15\%$ score bonus for quantity parity within $10\%$, $-15\%$ penalty for pack-size divergence.

### 3. Serving & UI Layer
- **Backend**: FastAPI asynchronous application factory exposing `GET /search`.
- **Caching**: Thread-safe in-memory `TTLCache` indexed by normalized `(query, location)` with a default 300-second eviction TTL.
- **Frontend**: Lightweight, dependency-free static bundle (`index.html`, `styles.css`, `app.js`) served by FastAPI `StaticFiles`.
