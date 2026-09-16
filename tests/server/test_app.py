from fastapi.testclient import TestClient

from app.server.app import create_app
from app.types import RawListing

MAGGI_BLINKIT = RawListing(
    platform="blinkit",
    name="Maggi 2-Minute Noodles 140 g",
    price=14.0,
    quantity="140 g",
    in_stock=True,
)
MAGGI_INSTAMART = RawListing(
    platform="instamart",
    name="Maggi 2-Minute Noodles 140 g",
    price=12.0,
    quantity="140 g",
    in_stock=True,
)


async def fake_blinkit(query: str, location: str) -> list[RawListing]:
    return [MAGGI_BLINKIT]


async def fake_instamart(query: str, location: str) -> list[RawListing]:
    return [MAGGI_INSTAMART]


def test_returns_matched_results_for_a_valid_query_and_location():
    app = create_app(fake_blinkit, fake_instamart)
    client = TestClient(app)

    res = client.get("/search", params={"q": "Maggi", "location": "Hostel Block A"})

    assert res.status_code == 200
    body = res.json()
    assert body["query"] == "Maggi"
    assert body["location"] == "Hostel Block A"
    assert len(body["results"]) == 1
    assert body["results"][0]["cheaper"] == "instamart"


def test_rejects_a_request_missing_query_or_location():
    app = create_app(fake_blinkit, fake_instamart)
    client = TestClient(app)

    res = client.get("/search", params={"q": "Maggi"})
    assert res.status_code == 400

    res2 = client.get("/search", params={"location": "Hostel Block A"})
    assert res2.status_code == 400


def test_still_returns_the_working_platform_if_the_other_fails():
    async def failing_instamart(query: str, location: str) -> list[RawListing]:
        raise RuntimeError("Instamart unreachable")

    app = create_app(fake_blinkit, failing_instamart)
    client = TestClient(app)

    res = client.get("/search", params={"q": "Maggi", "location": "Hostel Block A"})

    assert res.status_code == 200
    body = res.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["blinkit"] is not None
    assert body["results"][0]["instamart"] is None


def test_serves_repeated_identical_queries_from_cache():
    call_count = {"n": 0}

    async def counting_blinkit(query: str, location: str) -> list[RawListing]:
        call_count["n"] += 1
        return [MAGGI_BLINKIT]

    app = create_app(counting_blinkit, fake_instamart)
    client = TestClient(app)

    client.get("/search", params={"q": "Maggi", "location": "Hostel Block A"})
    client.get("/search", params={"q": "maggi", "location": "hostel block a"})

    assert call_count["n"] == 1
