import logging
from urllib.parse import quote_plus

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from app.scrapers.playwright_runner import run_playwright
from app.types import RawListing

logger = logging.getLogger(__name__)

BLINKIT_SEARCH_URL = "https://blinkit.com/s/?q="
DEFAULT_TIMEOUT_MS = 20000


async def _search_blinkit_impl(query: str, location: str, headless: bool) -> list[RawListing]:
    """
    Intercepts Blinkit's internal search API response instead of parsing the DOM.
    Blinkit loads products via XHR after page load - we capture that JSON directly.
    """
    target_url = f"{BLINKIT_SEARCH_URL}{quote_plus(query.strip())}"
    api_data = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        captured = []

        async def handle_response(response):
            try:
                url = response.url
                if (
                    "blinkit.com" in url
                    and response.status == 200
                    and ("search" in url or "product" in url or "listing" in url)
                    and "application/json" in (response.headers.get("content-type", ""))
                ):
                    data = await response.json()
                    captured.append(data)
                    logger.debug("Blinkit API captured: %s (%d bytes)", url, len(str(data)))
            except Exception:
                pass

        page.on("response", handle_response)

        try:
            await page.goto(target_url, timeout=DEFAULT_TIMEOUT_MS, wait_until="domcontentloaded")
            # Wait for API calls to fire and complete
            await page.wait_for_timeout(5000)
        except Exception as exc:
            logger.warning("Blinkit navigation error: %s", exc)
        finally:
            await browser.close()

    # Parse listings from captured API responses
    listings: list[RawListing] = []
    for data in captured:
        listings.extend(_extract_blinkit_listings(data))

    # Fallback: if API intercept yielded nothing, dump HTML for diagnosis
    if not listings:
        logger.warning("Blinkit: no listings captured from API (got %d responses)", len(captured))

    logger.info("Blinkit fetched %d listings", len(listings))
    return listings


def _extract_blinkit_listings(data: dict) -> list[RawListing]:
    """Recursively search the Blinkit API JSON for product objects."""
    results: list[RawListing] = []
    _walk_blinkit(data, results)
    return results


def _walk_blinkit(obj, results: list, depth: int = 0):
    if depth > 10:
        return
    if isinstance(obj, dict):
        # Check if this object looks like a product
        if "name" in obj and ("mrp" in obj or "price" in obj or "selling_price" in obj):
            name_raw = obj.get("name")
            if isinstance(name_raw, str):
                name = name_raw.strip()
                price_val = obj.get("price") or obj.get("mrp") or obj.get("selling_price") or 0
                try:
                    price = float(str(price_val).replace(",", "").replace("\u20b9", "").strip())
                except (ValueError, TypeError):
                    price = 0.0
                quantity = (
                    obj.get("unit", "")
                    or obj.get("weight", "")
                    or obj.get("pack_size", "")
                    or "1 unit"
                )
                if name and price > 0:
                    results.append(
                        RawListing(
                            platform="blinkit",
                            name=name,
                            price=price,
                            quantity=str(quantity),
                            in_stock=bool(obj.get("is_available", obj.get("in_stock", True))),
                            image_url=obj.get("image_url") or obj.get("img_url"),
                        )
                    )
        # Recurse into sub-dicts
        for v in obj.values():
            if isinstance(v, (dict, list)):
                _walk_blinkit(v, results, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                _walk_blinkit(item, results, depth + 1)


async def search_blinkit(query: str, location: str = "", headless: bool = True) -> list[RawListing]:
    """
    Search Blinkit by intercepting its internal search API JSON response.
    Runs Playwright in a dedicated thread with a ProactorEventLoop to avoid
    the NotImplementedError caused by Uvicorn'\''s SelectorEventLoop on Windows.
    """
    if not query.strip():
        return []
    return await run_playwright(lambda: _search_blinkit_impl(query, location, headless))
