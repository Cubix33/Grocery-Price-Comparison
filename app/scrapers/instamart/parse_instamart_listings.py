import re
from bs4 import BeautifulSoup

from app.types import RawListing

SELECTORS = {
    "card": ".item-widget-container, [data-testid='item-card'], div[class*='ItemCard__container']",
    "name": ".item-name, [data-testid='item-name'], div[class*='ItemCard__name'], div[class*='item-name']",
    "quantity": ".item-quantity, [data-testid='item-quantity'], div[class*='ItemCard__quantity'], div[class*='item-quantity']",
    "price": ".item-price, [data-testid='item-price'], div[class*='ItemCard__price'], div[class*='item-price']",
    "stock": ".item-availability, [data-testid='item-availability'], div[class*='ItemCard__availability'], div[class*='availability']",
}


def parse_instamart_listings(html: str) -> list[RawListing]:
    """
    Parse Swiggy Instamart product listings from an HTML document snapshot.
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
        in_stock = not ("sold out" in stock_text or "out of stock" in stock_text)

        listings.append(
            RawListing(
                platform="instamart",
                name=name,
                price=price,
                quantity=quantity or "1 unit",
                in_stock=in_stock,
            )
        )

    return listings
