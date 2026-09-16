from pathlib import Path

from app.scrapers.instamart.parse_instamart_listings import parse_instamart_listings

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "instamart_search_maggi.html"


def test_parses_listings_from_a_saved_instamart_search_results_page():
    html = FIXTURE.read_text(encoding="utf-8")

    listings = parse_instamart_listings(html)

    assert len(listings) == 2
    assert listings[0].platform == "instamart"
    assert listings[0].name == "Maggi 2-Minute Noodles"
    assert listings[0].price == 12.0
    assert listings[0].quantity == "140 g"
    assert listings[0].in_stock is True

    assert listings[1].platform == "instamart"
    assert listings[1].name == "Maggi Masala Noodles Family Pack"
    assert listings[1].price == 54.0
    assert listings[1].quantity == "560 g"
    assert listings[1].in_stock is False
