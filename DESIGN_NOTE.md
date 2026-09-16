# One-Page Design Note: The Great Grocery Price Race

**Author:** Anshika Singh (NSUT '26) • **Role:** AI Engineer / Full-Stack • **Submission:** CarDekho Group Campus Challenge

---

### 1. Overall Architecture & Trade-offs Considered

The application is structured into **three decoupled seams**:
1. **Fetch / Scraping Layer (`app/scrapers`)**: Platform-isolated drivers (Blinkit & Instamart) split into headless browser interaction (`Playwright`) and pure DOM extraction (`BeautifulSoup4`).
2. **Matching Engine (`app/matching`)**: A pure, stateless bipartite matching function driven by token-set ratio fuzzy scoring and unit-aware pack-size normalization.
3. **Orchestration & Serving Layer (`app/server`)**: A FastAPI ASGI service running both scrapers concurrently via `asyncio.gather(..., return_exceptions=True)`, fronted by an in-memory monotonic TTL cache and a zero-build static client.

#### Why This Over Alternatives?
- **Headless Browser (Playwright) vs. Raw HTTP Requests**: Both Blinkit and Swiggy Instamart are dynamic Single Page Applications (SPAs) that heavily gate catalog hydration behind client-side geohash resolution and store cookies. Raw HTTP requests with `requests` fail or yield empty initial DOM shells without JavaScript execution. Playwright provides built-in `networkidle` synchronization and reliable DOM state capture.
- **Pure Parser Decoupling vs. Monolithic Scraping**: By separating the Playwright page driver from the BeautifulSoup DOM parser, the entire test suite runs offline against saved HTML fixtures (`fixtures/*.html`). This ensures 100% deterministic CI runs, sub-second test execution (0.9s for 24 tests), and zero unnecessary request load on target platforms.
- **Async Gathering with Partial-Failure Resilience**: If one platform encounters a timeout or bot check, `return_exceptions=True` catches the error. The user still receives results from the working platform rather than experiencing an unhandled HTTP 500 crash.

---

### 2. "Same Product" Matching Logic & Honest Failure Modes

The matching engine pairs listings through a 3-stage heuristic pipeline:
1. **Canonical Normalization**: Cleans punctuation, lowercases, removes filler stopwords (`the`, `pack`, `of`), and extracts quantities via regex (`kg`, `g`, `l`, `ml`, `pcs`), converting them into canonical base units ($1\text{ kg} \to 1000\text{ g}$, $1\text{ L} \to 1000\text{ ml}$).
2. **Fuzzy String Alignment**: Computes `rapidfuzz.fuzz.token_set_ratio` between normalized names. This handles word reorderings (e.g., *"Maggi 2-Minute Noodles"* vs. *"Noodles 2-Minute Maggi"*).
3. **Unit-Aware Quantity Verification**:
   - If both items specify identical units: items within a $15\%$ quantity tolerance receive a $+15$ score bonus.
   - If quantities diverge beyond $25\%$ (e.g., $70\text{ g}$ single pack vs. $560\text{ g}$ family pack), pairing is strictly rejected. This prevents false comparisons where a smaller pack appears deceptive as "cheaper".
   - Items with incompatible units (e.g., volume $\text{ml}$ vs. weight $\text{g}$) are blocked from pairing.

#### Where This Logic Breaks Down (Real-World Edge Cases):
1. **Multipacks vs. Net Weight Discrepancies**: A *"Pack of 4 (70g each)"* may be described as *"4 x 70g"* on Blinkit but *"280g"* on Instamart. Without an explicit multipack multiplication parser, token extraction might compare $4\text{ pcs}$ against $280\text{ g}$ and reject the match.
2. **Private-Label Exclusives**: Blinkit’s *Blinkit Selection* / *B-Choice* or Instamart’s *Supreme* brands have no cross-platform equivalent. The heuristic correctly isolates them as unpaired listings, but cannot recommend substitute cross-brand equivalents.
3. **Flavors & Variant Collision**: Products sharing identical brands and base tokens (e.g., *"Lay's Spanish Tomato Tango 50g"* vs. *"Lay's Magic Masala 50g"*) achieve high token overlap ($\sim 75\%$). Without dedicated SKU/flavor vector embeddings, high-order n-gram collisions can occasionally mismatch adjacent flavor variants.
4. **Density Inconsistencies**: Ice cream and dairy products often list either grams ($g$) or volume ($ml$) interchangeably across retailers depending on aeration, preventing unit unification under pure regex rules.

---

### 3. Scaling Roadmap: Multiple Locations & High Concurrency

To transition this proof-of-concept into a production-grade comparison system supporting millions of queries across hundreds of pin codes:

1. **Pre-fetching & Dark Store Geohash Clustering**:
   - Quick commerce inventories are partitioned by hyper-local dark stores ($\sim 2\text{--}3\text{ km}$ radiuses). Rather than launching on-demand browsers per search, reverse geocode delivery coordinates into dark store IDs.
   - Run scheduled background ingestion workers for the top 5,000 grocery SKUs per active dark store into a centralized database, serving user searches in $<50\text{ ms}$ directly from Redis/PostgreSQL.
2. **Distributed Browser Pool & Proxy Rotation**:
   - For on-demand long-tail queries, replace ephemeral local Chromium instances with a pool of managed headless workers (e.g., Playwright on Browserless.io / AWS ECS) behind residential rotating proxies to prevent IP rate-limiting and Cloudflare challenges.
3. **Vector / Embedding Search for Product Matching**:
   - Replace heuristic token ratios with a two-stage retrieval pipeline: fine-tuned Sentence-Transformers (e.g., `all-MiniLM-L6-v2` or multi-modal CLIP on product images + titles) storing embeddings in Qdrant/pgvector, followed by strict deterministic unit/pack validation gates.
