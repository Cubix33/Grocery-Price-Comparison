from typing import Literal, Optional
from rapidfuzz import fuzz

from app.matching.normalize import normalize_name, parse_quantity
from app.types import MatchedPair, RawListing

NAME_MATCH_THRESHOLD = 55.0  # rapidfuzz token_set_ratio baseline
QUANTITY_MATCH_TOLERANCE = 0.15  # 15% tolerance for slight packaging variance
QUANTITY_MAX_ALLOWED_DIFF = 0.25  # 25% max allowed difference before rejecting as different pack size
QUANTITY_MATCH_BONUS = 15.0
QUANTITY_MISMATCH_PENALTY = 50.0



def _pick_cheaper(a: RawListing, b: RawListing) -> Literal["blinkit", "instamart", "tie"]:
    if a.price == b.price:
        return "tie"
    return a.platform if a.price < b.price else b.platform


def match_listings(
    blinkit_listings: list[RawListing],
    instamart_listings: list[RawListing],
) -> list[MatchedPair]:
    """
    Greedy bipartite matching of listings from Blinkit and Instamart.
    Pairs items based on token-set similarity and quantity compatibility.
    """
    pairs: list[MatchedPair] = []
    used_instamart: set[int] = set()

    for blinkit_item in blinkit_listings:
        blinkit_norm = normalize_name(blinkit_item.name)
        blinkit_qty = parse_quantity(blinkit_item.name) or parse_quantity(blinkit_item.quantity)

        best_index = -1
        best_score = 0.0

        for index, instamart_item in enumerate(instamart_listings):
            if index in used_instamart:
                continue

            instamart_norm = normalize_name(instamart_item.name)
            score = float(fuzz.token_set_ratio(blinkit_norm, instamart_norm))

            instamart_qty = parse_quantity(instamart_item.name) or parse_quantity(instamart_item.quantity)

            # Check quantity compatibility
            if blinkit_qty and instamart_qty:
                if blinkit_qty.unit == instamart_qty.unit:
                    base_val = max(blinkit_qty.value, instamart_qty.value)
                    min_val = min(blinkit_qty.value, instamart_qty.value)
                    diff = (base_val - min_val) / base_val if base_val > 0 else 0.0

                    if diff > QUANTITY_MAX_ALLOWED_DIFF:
                        # Different pack size (e.g. 70g vs 560g) - do not pair
                        continue
                    elif diff <= QUANTITY_MATCH_TOLERANCE:
                        score += QUANTITY_MATCH_BONUS
                    else:
                        score -= QUANTITY_MISMATCH_PENALTY
                else:
                    # Incompatible units (e.g. ml vs g)
                    continue

            if score > best_score:
                best_score = score
                best_index = index

        if best_index >= 0 and best_score >= NAME_MATCH_THRESHOLD:
            used_instamart.add(best_index)
            instamart_item = instamart_listings[best_index]
            pairs.append(
                MatchedPair(
                    blinkit=blinkit_item,
                    instamart=instamart_item,
                    similarity=round(min(best_score, 100.0) / 100.0, 2),
                    cheaper=_pick_cheaper(blinkit_item, instamart_item),
                )
            )
        else:
            pairs.append(
                MatchedPair(
                    blinkit=blinkit_item,
                    instamart=None,
                    similarity=0.0,
                    cheaper=None,
                )
            )

    # Append any remaining unmatched Instamart listings
    for index, item in enumerate(instamart_listings):
        if index not in used_instamart:
            pairs.append(
                MatchedPair(
                    blinkit=None,
                    instamart=item,
                    similarity=0.0,
                    cheaper=None,
                )
            )

    return pairs
