import logging
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import re

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from app.scrapers.playwright_runner import run_playwright
from app.types import RawListing

logger = logging.getLogger(__name__)

INSTAMART_SEARCH_URL = "https://www.swiggy.com/instamart/search?query="
DEFAULT_TIMEOUT_MS = 20000


async def _search_instamart_impl(query: str, location: str, headless: bool) -> list[RawListing]:
    """
    Search Swiggy Instamart by scraping the SSR HTML since the API is WAF-protected.
    Runs Playwright in a dedicated thread with a ProactorEventLoop.
    """
    target_url = f"{INSTAMART_SEARCH_URL}{quote_plus(query.strip())}"
    html = ""

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
            await page.goto(target_url, timeout=DEFAULT_TIMEOUT_MS, wait_until="domcontentloaded")
            # Wait for data-testid="item-collection-card" to appear, or for 'MINS'
            try:
                await page.wait_for_selector(
                    "div[data-testid*='item-collection-card']",
                    timeout=8000,
                )
            except PlaywrightTimeoutError:
                pass
            html = await page.content()
        except Exception as exc:
            logger.warning("Instamart navigation error: %s", exc)
        finally:
            await browser.close()

    listings = parse_instamart_html(html)
    logger.info("Instamart fetched %d listings", len(listings))
    return listings


def parse_instamart_html(html: str) -> list[RawListing]:
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    # Cards have data-testid="item-collection-card" or "item-collection-card-full"
    cards = soup.find_all(attrs={"data-testid": lambda x: x and "item-collection-card" in x})
    
    listings = []
    seen = set()
    
    for c in cards:
        parent = c.parent
        texts = [t.strip() for t in parent.stripped_strings if t.strip()]
        if not texts:
            continue
            
        name = ""
        quantity = "1 unit"
        price = 0.0
        in_stock = True
        
        # Determine out of stock
        lower_texts = [t.lower() for t in texts]
        if any("out of stock" in t or "sold out" in t for t in lower_texts):
            in_stock = False
            
        # Filter out badges
        skip_words = ["bestseller", "ad", "sponsored", "mins"]
        filtered = []
        for t in texts:
            if any(w in t.lower() for w in skip_words) and len(t) < 15:
                continue
            filtered.append(t)
            
        if not filtered:
            continue
            
        name = filtered[0] # Usually the name is the first substantial string after badges
        
        # Quantity usually has numbers and units
        qty_pattern = re.compile(r"^\d+(\.\d+)?\s*(g|kg|ml|l|pc|pcs|pack|units)$", re.IGNORECASE)
        for i, t in enumerate(filtered[1:]):
            if qty_pattern.match(t):
                quantity = t
                break
        
        # Price is typically the string right after "% OFF" or the last numeric string
        price_found = False
        for i, t in enumerate(filtered):
            if "% off" in t.lower() and i + 1 < len(filtered):
                # The next string is usually the selling price
                val = re.sub(r"[^\d.]", "", filtered[i+1])
                if val:
                    price = float(val)
                    price_found = True
                    break
                    
        if not price_found:
            # Look backwards for the first numeric string
            for t in reversed(filtered):
                val = re.sub(r"[^\d.]", "", t)
                if val and len(val) == len(t.replace("\u20b9", "").replace("Rs", "").strip()):
                    price = float(val)
                    break
        
        if name and price > 0:
            key = f"{name}-{quantity}-{price}"
            if key not in seen:
                seen.add(key)
                listings.append(
                    RawListing(
                        platform="instamart",
                        name=name,
                        price=price,
                        quantity=quantity,
                        in_stock=in_stock,
                    )
                )
                
    return listings

async def search_instamart(query: str, location: str = "", headless: bool = True) -> list[RawListing]:
    if not query.strip():
        return []
    return await run_playwright(lambda: _search_instamart_impl(query, location, headless))
