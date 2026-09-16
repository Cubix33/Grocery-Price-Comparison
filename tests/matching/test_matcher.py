from app.matching.matcher import match_listings
from app.types import RawListing


def make_listing(**overrides) -> RawListing:
    defaults = dict(
        platform="blinkit",
        name="Maggi 2-Minute Noodles 140 g",
        price=14.0,
        quantity="140 g",
        in_stock=True,
    )
    defaults.update(overrides)
    return RawListing(**defaults)


def test_matches_identical_products_with_same_pack_size():
    blinkit = [make_listing(platform="blinkit", price=14.0)]
    instamart = [make_listing(platform="instamart", price=12.0)]

    pairs = match_listings(blinkit, instamart)

    assert len(pairs) == 1
    assert pairs[0].blinkit is not None
    assert pairs[0].instamart is not None
    assert pairs[0].cheaper == "instamart"


def test_does_not_match_same_name_with_very_different_pack_sizes():
    blinkit = [make_listing(platform="blinkit", name="Maggi 2-Minute Noodles 70 g", quantity="70 g")]
    instamart = [
        make_listing(
            platform="instamart",
            name="Maggi 2-Minute Noodles 560 g (Family Pack)",
            quantity="560 g",
        )
    ]

    pairs = match_listings(blinkit, instamart)

    assert len(pairs) == 2
    assert all(p.blinkit is None or p.instamart is None for p in pairs)


def test_leaves_unmatched_items_from_either_platform_unpaired():
    blinkit = [make_listing(platform="blinkit", name="Amul Butter 500 g", quantity="500 g")]
    instamart = [make_listing(platform="instamart", name="Britannia Bread 400 g", quantity="400 g")]

    pairs = match_listings(blinkit, instamart)

    assert len(pairs) == 2
    blinkit_pair = next(p for p in pairs if p.blinkit is not None)
    instamart_pair = next(p for p in pairs if p.instamart is not None)
    assert blinkit_pair.instamart is None
    assert instamart_pair.blinkit is None


def test_picks_the_best_of_several_candidates_on_the_other_platform():
    blinkit = [make_listing(platform="blinkit", name="Amul Butter 500 g", quantity="500 g")]
    instamart = [
        make_listing(platform="instamart", name="Amul Cheese 500 g", quantity="500 g"),
        make_listing(platform="instamart", name="Amul Butter 500 g", quantity="500 g"),
    ]

    pairs = match_listings(blinkit, instamart)
    matched = next(p for p in pairs if p.blinkit is not None and p.instamart is not None)

    assert matched.instamart is not None
    assert matched.instamart.name == "Amul Butter 500 g"


def test_reports_a_tie_when_prices_are_equal():
    blinkit = [make_listing(platform="blinkit", price=20.0)]
    instamart = [make_listing(platform="instamart", price=20.0)]

    pairs = match_listings(blinkit, instamart)

    assert len(pairs) == 1
    assert pairs[0].cheaper == "tie"
