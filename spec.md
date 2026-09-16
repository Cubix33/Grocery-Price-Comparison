Spec: Grocery Price Compare — "The Great Grocery Price Race"
CarDekho Group AI Assignment (NSUT '26) — greenfield build, no existing codebase or issue tracker detected, so this spec is written as a standalone planning document rather than published to a tracker.

Problem Statement
A hostel resident wants to buy a grocery item (e.g. "Maggi" or "Amul butter") and doesn't know whether it's cheaper on Blinkit or Instamart. Today, finding out means opening two separate apps, searching the same item twice, and manually comparing prices and stock — a slow, repetitive, error-prone process that people give up on and just guess.

Solution
A single web app where the user types one search query and picks a delivery location once, and the app shows matching listings and prices from both Blinkit and Instamart side by side, so the price comparison that currently takes two app-switches and manual squinting takes one search.

User Stories
As a user, I want to type a grocery item name into a single search box, so that I don't have to search twice across two apps.
As a user, I want to set my delivery location once (address, pincode, or lat/long), so that prices reflect what I'd actually be charged and what's actually deliverable to me.
As a user, I want to see Blinkit results and Instamart results in the same view, so that I can compare them without switching screens.
As a user, I want each listing to show item name, price, pack size/quantity, and platform, so that I can judge whether two listings are really "the same product" myself if the app's matching is uncertain.
As a user, I want the app to visually pair up listings it believes are the same product across platforms, so that I can see the price difference at a glance instead of scanning two separate lists.
As a user, I want to see which platform is cheaper for a given item (or pack size), so that I can make the decision in seconds.
As a user, I want to see stock/availability status per platform, so that I don't pick the "cheaper" option only to find it's out of stock.
As a user, I want a reasonable fallback when a query matches product on only one platform, so that I still get useful results instead of a blank screen.
As a user, I want a clear "no results" or "nothing matched" state, so that I know the search genuinely failed rather than the app being broken.
As a user, I want the search to return results within a few seconds, so that the tool is actually faster than opening both apps myself.
As a user, I want to see a loading state while both platforms are being queried, so that I know the app is working and not frozen.
As a user, I want an error message (not a crash) if one platform's site is unreachable or its page structure changed, so that I still get results from the platform that worked.
As a developer evaluating this submission, I want a README with setup and run steps that work on a fresh machine, so that I can run the app without knowing the stack in advance.
As a developer evaluating this submission, I want a one-page design note covering architecture, product-matching logic (and its failure modes), and scaling considerations, so that I can assess the reasoning behind the build, not just the UI.
As a developer evaluating this submission, I want a 1-minute screen recording of the app working end to end, so that I can verify it functions without having to set it up myself first.
As the site owner (Blinkit/Instamart), I want the scraping request volume to stay reasonable, so that the assignment doesn't place undue load on production infrastructure.
As a user, I want the app to work without me logging into Blinkit, Instamart, or the app itself, so that I can use it immediately with zero setup friction.
As a user typing a misspelled or brand-shorthand query (e.g. "maggi" vs "Maggi 2-Minute Noodles"), I want the app to still return relevant matches, so that exact string matching doesn't cause false negatives.
As a user, I want pack-size differences (e.g. 70g vs 140g Maggi) to be reflected in the comparison, so that I'm not misled by a lower price that's actually a smaller quantity.
As a user, I want to change my delivery location and re-run the search, so that I can check prices for a different hostel/PG/address.
Implementation Decisions
Architecture. Three seams, kept to the minimum needed to test independently:

Fetch/Scrape layer — one module per platform (BlinkitSource, InstamartSource) responsible only for taking a (query, location) pair and returning raw listings (name, price, pack size, stock, image/url if available). This is the seam most likely to break (site structure changes), so it's isolated behind a common interface (search(query, location) -> RawListing[]) so the rest of the app never depends on scraping internals directly.
Matching/normalization layer — a pure function seam: matchListings(blinkitListings, instamartListings) -> MatchedPair[]. Pure and side-effect-free by design, so it's the highest-leverage place to put automated tests (no network, no browser needed).
API + UI layer — a thin backend endpoint (GET /search?q=&location=) that orchestrates the two fetch calls in parallel, runs the matcher, and returns JSON; a simple frontend (single search box + location picker + two-column or paired-card results view) consumes it.
Given desktop-site-only scraping is required (no reverse-engineered APIs), the fetch layer uses a headless browser (Playwright preferred over Puppeteer for built-in network idle/wait-for-selector ergonomics and easier location-cookie/session handling) rather than raw HTTP + HTML parsing, since both platforms are JS-rendered SPAs that gate results behind a selected delivery location.

Location handling. Location is set once per session (address autocomplete or manual pincode entry) and passed into both scrapers, which set it via each site's location-picker flow before searching, since both platforms return different catalogs/prices depending on serviceable delivery location.

Product matching ("same product" logic). Normalize each listing's name (lowercase, strip pack-size tokens, strip stopwords/brand filler), extract a structured {brand, product, quantity, unit} where possible via regex/heuristics, then score candidate pairs using a combination of normalized-string similarity (token-set ratio) and quantity/unit agreement. Pairs above a similarity threshold are shown as matched; everything else is shown unmatched under its own platform. This is a heuristic, not authoritative — the design note explicitly documents where it breaks (private-label products with no equivalent, different pack sizes marketed as the "same" item, multipacks vs singles, near-duplicate flavor variants).

Caching/rate limiting. In-memory (or simple file-based) cache keyed by (normalized query, location) with a short TTL, so repeated searches during demoing/testing don't repeatedly hit the live sites, in line with the "keep request volume reasonable" ground rule.

Stack. Left to the builder's judgment per the assignment ("any language/framework"), but whatever is chosen should keep the three seams above separately runnable/testable — e.g. Node/TypeScript + Playwright + Express + a minimal React or plain HTML/JS frontend, or Python + Playwright + FastAPI + a minimal frontend.

Testing Decisions
Good tests here exercise external behavior, not scraper internals: given a fixed HTML/DOM fixture captured from each site, does the fetch layer produce the correct structured listings? Given two lists of structured listings, does the matcher produce the expected pairs?
Fetch layer: tested against saved HTML fixtures (captured once, checked into the repo) rather than live network calls in CI, so tests are deterministic and don't hammer the real sites — directly serves the "reasonable request volume" ground rule.
Matching layer: the highest-value module to test, since it's pure and the core intellectual content of the assignment. Table-driven tests covering: exact match, pack-size mismatch, brand-only match, no match, ambiguous multi-candidate match.
API layer: a handful of integration tests hitting /search with mocked fetch-layer responses, verifying correct orchestration (both platforms queried in parallel, partial failure handled gracefully, response shape is correct).
No prior art in-repo (greenfield project) — these conventions are proposed fresh rather than inherited.
Out of Scope
User accounts, login, or saved locations across sessions.
A native/mobile app.
Reverse-engineering either platform's mobile APK or private APIs.
Supporting more than one delivery location at a time in a single search.
Production deployment or public hosting (explicitly disallowed by the ground rules — the app must not be deployed or shared outside the assignment).
Exhaustive category coverage beyond grocery/food items.
Real-time price tracking or historical price trends.
Further Notes
Submission checklist (from the assignment, not implementation work): zipped code excluding node_modules/venvs/build output; README with fresh-machine setup steps; the one-page design note inside the zip covering architecture rationale, matching-logic limitations, and what changes at scale; a 1-minute unlisted screen recording; all submitted via the linked Google Form before the deadline.
The design note is explicitly called out as "the part we read most closely" — it should be written as carefully as the code, especially the honest discussion of where product-matching breaks down.
Grading is on reasoning and scoping under a messy real-world problem, not UI polish — implementation effort is best spent on the matching heuristic and the design note, not visual design.