from typing import Literal, Optional
from pydantic import BaseModel

Platform = Literal["blinkit", "instamart"]


class RawListing(BaseModel):
    platform: Platform
    name: str
    price: float
    quantity: str  # raw pack-size string as displayed, e.g. "140 g"
    in_stock: bool = True
    image_url: Optional[str] = None
    url: Optional[str] = None


class MatchedPair(BaseModel):
    blinkit: Optional[RawListing] = None
    instamart: Optional[RawListing] = None
    similarity: float = 0.0
    cheaper: Optional[Literal["blinkit", "instamart", "tie"]] = None
