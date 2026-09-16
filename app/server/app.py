import asyncio
import logging
from typing import Awaitable, Callable, Optional

from fastapi import FastAPI, HTTPException, Query

from app.matching.matcher import match_listings
from app.server.cache import TTLCache, cache_key
from app.types import RawListing

logger = logging.getLogger(__name__)

SearchFn = Callable[[str, str], Awaitable[list[RawListing]]]


class CachedResult:
    def __init__(self, blinkit: list[RawListing], instamart: list[RawListing]):
        self.blinkit = blinkit
        self.instamart = instamart


def create_app(
    search_blinkit: SearchFn,
    search_instamart: SearchFn,
    cache: Optional[TTLCache[CachedResult]] = None,
) -> FastAPI:
    """
    Application factory for the Grocery Price Compare backend.
    Takes decoupled search functions for dependency injection and testing.
    """
    cache = cache or TTLCache[CachedResult](ttl_seconds=300.0)
    app = FastAPI(title="Grocery Price Compare API", version="1.0.0")

    @app.get("/search")
    async def search(q: str = Query(default=""), location: str = Query(default="")):
        query = q.strip()
        loc = location.strip()

        if not query or not loc:
            raise HTTPException(status_code=400, detail="q and location are both required")

        key = cache_key(query, loc)
        cached = cache.get(key)

        if cached is None:
            # Query platforms concurrently with partial failure resilience
            blinkit_result, instamart_result = await asyncio.gather(
                search_blinkit(query, loc),
                search_instamart(query, loc),
                return_exceptions=True,
            )

            if isinstance(blinkit_result, Exception):
                logger.error("Blinkit fetch error: %s", blinkit_result)
                blinkit_listings: list[RawListing] = []
            else:
                blinkit_listings = blinkit_result

            if isinstance(instamart_result, Exception):
                logger.error("Instamart fetch error: %s", instamart_result)
                instamart_listings: list[RawListing] = []
            else:
                instamart_listings = instamart_result

            cached = CachedResult(blinkit_listings, instamart_listings)
            cache.set(key, cached)

        results = match_listings(cached.blinkit, cached.instamart)
        return {
            "query": query,
            "location": loc,
            "results": [r.model_dump() for r in results],
        }

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
