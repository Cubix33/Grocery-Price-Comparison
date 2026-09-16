# Requirements Delta: 001-core-implementation

## Delta Overview
Initial greenfield build implementing the baseline specification defined in `aidlc-docs/inception/requirements.md` and `spec.md`.

## Detailed Deliverables
- **NEW**: Core domain Pydantic schemas (`RawListing`, `MatchedPair`).
- **NEW**: Canonical unit conversion (`kg->g`, `l->ml`) and text normalization logic.
- **NEW**: Weighted fuzzy similarity matcher using `rapidfuzz` with pack-size scoring.
- **NEW**: Decoupled HTML parser fixtures for Blinkit and Instamart.
- **NEW**: Playwright async browser automation drivers.
- **NEW**: In-memory monotonic TTL search cache.
- **NEW**: FastAPI `/search` endpoint with partial failure resilience.
- **NEW**: Static frontend interface.
- **NEW**: Unit & integration test suite.
- **NEW**: One-page design note covering architecture trade-offs, matching heuristics, and scale roadmap.
