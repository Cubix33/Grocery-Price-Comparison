from app.types import RawListing, MatchedPair


def test_raw_listing_and_matched_pair_hold_expected_fields():
    listing = RawListing(
        platform="blinkit",
        name="Maggi 2-Minute Noodles",
        price=14.0,
        quantity="140 g",
        in_stock=True,
    )

    pair = MatchedPair(blinkit=listing, instamart=None, similarity=0.0, cheaper=None)

    assert pair.blinkit is not None
    assert pair.blinkit.platform == "blinkit"
    assert pair.blinkit.name == "Maggi 2-Minute Noodles"
    assert pair.blinkit.price == 14.0
    assert pair.blinkit.quantity == "140 g"
    assert pair.blinkit.in_stock is True
    assert pair.instamart is None
    assert pair.similarity == 0.0
    assert pair.cheaper is None
