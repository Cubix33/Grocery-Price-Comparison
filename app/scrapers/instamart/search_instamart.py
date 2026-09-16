import asyncio
import logging
from urllib.parse import quote_plus
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from app.scrapers.instamart.parse_instamart_listings import parse_instamart_listings
from app.types import RawListing

logger = logging.getLogger(__name__)

INSTAMART_SEARCH_URL = "https://www.swiggy.com/instamart/search?query="
DEFAULT_TIMEOUT_MS = 15000


async def search_instamart(query: str, location: str = "", headless: bool = True) -> list[RawListing]:
    """
    Search Swiggy Instamart using an asynchronous Playwright browser instance.
    Navigates to the search route, applies reasonable timeouts, and parses item cards.
    """
    if not query.strip():
        return []

    target_url = f"{INSTAMART_SEARCH_URL}{quote_plus(query.strip())}"

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

        try:
            # Navigate to search page
            await page.goto(target_url, timeout=DEFAULT_TIMEOUT_MS, wait_until="domcontentloaded")

            # Allow dynamic hydration
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except PlaywrightTimeoutError:
                pass

            # Wait briefly for item elements to render if present
            try:
                await page.wait_for_selector(
                    ".item-widget-container, [data-testid='item-card'], div[class*='ItemCard']",
                    timeout=4000,
                )
            except PlaywrightTimeoutError:
                pass

            html = await page.content()
            listings = parse_instamart_listings(html)
            return listings

        except Exception as exc:
            logger.warning("Instamart search encountered an error: %s", exc)
            return []
        finally:
            await browser.close()
