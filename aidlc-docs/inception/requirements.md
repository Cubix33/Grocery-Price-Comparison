# Baseline Requirements: The Great Grocery Price Race

## 1. Problem Statement
Hostel residents and everyday consumers frequently debate whether an essential grocery or snack item (e.g., Maggi, Amul Butter, milk, bread) is cheaper on Blinkit or Swiggy Instamart. Currently, comparing prices requires manually opening both applications, repeatedly searching the same item, and squinting at pack sizes, discount prices, and stock availability across screens.

## 2. Core Objectives
1. **Unified Search**: Accept a single grocery item search query and a target delivery location.
2. **Dual-Platform Retrieval**: Concurrently retrieve matching listings, real-time prices, pack sizes, and availability from both Blinkit and Swiggy Instamart desktop web platforms.
3. **Intelligent Cross-Platform Matching**: Determine whether a listing on Blinkit represents the "same product" as a listing on Instamart through semantic text normalization and unit-aware pack size verification.
4. **Actionable Price Comparison**: Present listings side by side, explicitly highlighting the cheaper platform, handling price ties, and clearly presenting single-platform fallbacks.
5. **Resilience & Rate Limiting**: Gracefully handle partial platform failures (e.g., timeout or DOM mutation on one platform) without crashing the search experience. Cache search results in-memory with a configurable TTL to respect target service infrastructure.

## 3. Non-Functional Requirements (NFRs)
- **Zero Authentication**: No user login or session management required.
- **Deterministic Testing**: Scraper parsers and matching logic must run offline against stored fixtures with zero live network calls in CI/test suites.
- **Portability**: Must execute reliably on any fresh environment with Python 3.11+ and standard pip dependencies.
- **Strict Compliance**: Desktop web scraping only; no reverse-engineering of proprietary mobile APKs or private APIs.
