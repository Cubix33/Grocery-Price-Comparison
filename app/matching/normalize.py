import re
from typing import Literal, NamedTuple, Optional

QUANTITY_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml|pcs|pc)\b", re.IGNORECASE)

UNIT_TO_BASE: dict[str, tuple[float, Literal["g", "ml", "pcs"]]] = {
    "kg": (1000.0, "g"),
    "g": (1.0, "g"),
    "l": (1000.0, "ml"),
    "ml": (1.0, "ml"),
    "pcs": (1.0, "pcs"),
    "pc": (1.0, "pcs"),
}


class ParsedQuantity(NamedTuple):
    value: float
    unit: Literal["g", "ml", "pcs"]


def parse_quantity(text: str) -> Optional[ParsedQuantity]:
    if not text:
        return None
    match = QUANTITY_PATTERN.search(text)
    if not match:
        return None
    raw_value = float(match.group(1))
    factor, base = UNIT_TO_BASE[match.group(2).lower()]
    return ParsedQuantity(value=raw_value * factor, unit=base)


STOPWORDS = {"the", "a", "an", "of", "with", "pack"}


def normalize_name(raw_name: str) -> str:
    if not raw_name:
        return ""
    without_quantity = QUANTITY_PATTERN.sub(" ", raw_name)
    lowered = without_quantity.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    tokens = [token for token in cleaned.split() if token and token not in STOPWORDS]
    return " ".join(tokens)
