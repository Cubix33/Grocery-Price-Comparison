# Baseline Technology Stack

| Layer | Selected Technology | Rationale |
|---|---|---|
| **Runtime** | Python 3.11+ / 3.12 | Standard, widespread support for modern async and typing. |
| **API Framework** | FastAPI + Uvicorn | High-performance asynchronous routing, Pydantic v2 serialization, interactive documentation. |
| **Browser Automation** | Playwright (async API) | Resilient headless Chromium driving with built-in networkidle synchronization, cleaner than Selenium/Puppeteer. |
| **HTML Parsing** | BeautifulSoup4 | Fast, resilient DOM navigation over static snapshots. |
| **Fuzzy Matching** | rapidfuzz | C++ backed, blazing-fast Levenshtein/token-set ratio computation outperforming fuzzywuzzy. |
| **Data Validation** | Pydantic v2 | Robust runtime typing and JSON serialization. |
| **Testing** | pytest + httpx (TestClient) | Industry standard test harness with fixture management and asynchronous HTTP assertion. |
| **Frontend** | Vanilla HTML5 / CSS3 / ES6 | Zero-build simplicity enabling instant execution on any fresh evaluation machine. |
