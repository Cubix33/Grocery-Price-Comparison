import asyncio
import logging
from urllib.parse import quote_plus
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from app.scrapers.blinkit.parse_blinkit_listings import parse_blinkit_listings
from app.types import RawListing

logger = logging.getLogger(__name__)

BLINKIT_SEARCH_URL = "https://blinkit.com/s/?q="
DEFAULT_TIMEOUT_MS = 15000


async def search_blinkit(query: str, location: str = "", headless: bool = True) -> list[RawListing]:
    """
    Search Blinkit using an asynchronous Playwright browser instance.
    Navigates to the search route, applies reasonable timeouts, and parses product cards.
    """
    if not query.strip():
        return []

    target_url = f"{BLINKIT_SEARCH_URL}{quote_plus(query.strip())}"

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
                pass  # Dynamic assets often keep connections open

            # Wait briefly for product card elements to render if present
            try:
                await page.wait_for_selector(
                    ".ProductCard, [data-test-id='product-card'], div[class*='Product']",
                    timeout=4000,
                )
            except PlaywrightTimeoutError:
                pass

            html = await page.content()
            listings = parse_blinkit_listings(html)
            return listings

        except Exception as exc:
            logger.warning("Blinkit search encountered an error: %s", exc)
            return []
        finally:
            await browser.close()
