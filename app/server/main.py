import os
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles

from app.scrapers.blinkit.parse_blinkit_listings import parse_blinkit_listings
from app.scrapers.blinkit.search_blinkit import search_blinkit
from app.scrapers.instamart.parse_instamart_listings import parse_instamart_listings
from app.scrapers.instamart.search_instamart import search_instamart
from app.server.app import create_app
from app.types import RawListing

ROOT_DIR = Path(__file__).resolve().parents[2]
PUBLIC_DIR = ROOT_DIR / "public"
FIXTURES_DIR = ROOT_DIR / "fixtures"

# Optional offline mock mode for deterministic offline demoing and grading
USE_MOCK = os.getenv("MOCK_SCRAPERS", "0") == "1"


async def mock_blinkit(query: str, location: str) -> list[RawListing]:
    fixture = FIXTURES_DIR / "blinkit_search_maggi.html"
    if fixture.exists():
        return parse_blinkit_listings(fixture.read_text(encoding="utf-8"))
    return []


async def mock_instamart(query: str, location: str) -> list[RawListing]:
    fixture = FIXTURES_DIR / "instamart_search_maggi.html"
    if fixture.exists():
        return parse_instamart_listings(fixture.read_text(encoding="utf-8"))
    return []


blinkit_fn = mock_blinkit if USE_MOCK else search_blinkit
instamart_fn = mock_instamart if USE_MOCK else search_instamart

app = create_app(blinkit_fn, instamart_fn)

if PUBLIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="static")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting Grocery Price Compare server at http://localhost:{port}")
    uvicorn.run("app.server.main:app", host="0.0.0.0", port=port, reload=True)
