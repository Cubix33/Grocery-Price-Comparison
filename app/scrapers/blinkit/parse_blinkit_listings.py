import re
from bs4 import BeautifulSoup

from app.types import RawListing

SELECTORS = {
    "card": ".ProductCard, [data-test-id='product-card'], div[class*='Product__wrapper']",
    "name": ".ProductCard__name, [data-test-id='product-name'], div[class*='Product__title'], div[class*='name']",
    "quantity": ".ProductCard__quantity, [data-test-id='product-unit'], div[class*='Product__unit'], div[class*='unit']",
    "price": ".ProductCard__price, [data-test-id='product-price'], div[class*='Product__price'], div[class*='price']",
    "stock": ".ProductCard__stock, [data-test-id='product-stock'], div[class*='Product__stock'], div[class*='stock']",
}


def parse_blinkit_listings(html: str) -> list[RawListing]:
    """
    Parse Blinkit product listings from an HTML document snapshot.
    Extracts name, price, quantity/pack-size, and stock status.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    listings: list[RawListing] = []

    cards = soup.select(SELECTORS["card"])
    for card in cards:
        name_el = card.select_one(SELECTORS["name"])
        quantity_el = card.select_one(SELECTORS["quantity"])
        price_el = card.select_one(SELECTORS["price"])
        stock_el = card.select_one(SELECTORS["stock"])

        name = name_el.get_text(strip=True) if name_el else ""
        quantity = quantity_el.get_text(strip=True) if quantity_el else ""
        price_text = price_el.get_text(strip=True) if price_el else ""
        stock_text = (stock_el.get_text(strip=True) if stock_el else "").lower()

        # Extract numeric price
        price_match = re.search(r"(\d+(?:\.\d+)?)", price_text.replace(",", ""))
        if not name or not price_match:
            continue

        price = float(price_match.group(1))
        in_stock = not ("out of stock" in stock_text or "sold out" in stock_text)

        listings.append(
            RawListing(
                platform="blinkit",
                name=name,
                price=price,
                quantity=quantity or "1 unit",
                in_stock=in_stock,
            )
        )

    return listings
