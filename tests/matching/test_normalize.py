from app.matching.normalize import normalize_name, parse_quantity


def test_parses_grams():
    result = parse_quantity("Amul Butter 500 g")
    assert result is not None
    assert result.value == 500
    assert result.unit == "g"


def test_converts_kg_to_grams():
    result = parse_quantity("Basmati Rice 1 kg")
    assert result is not None
    assert result.value == 1000
    assert result.unit == "g"


def test_converts_litres_to_ml():
    result = parse_quantity("Coca-Cola 1 L Bottle")
    assert result is not None
    assert result.value == 1000
    assert result.unit == "ml"


def test_parses_piece_counts():
    result = parse_quantity("Eggs 6 pcs")
    assert result is not None
    assert result.value == 6
    assert result.unit == "pcs"


def test_returns_none_when_no_quantity_present():
    assert parse_quantity("Assorted Snacks Combo") is None


def test_normalize_name_lowercases_strips_punctuation_and_quantity():
    assert normalize_name("Maggi 2-Minute Noodles, 140 g Pack") == "maggi 2 minute noodles"


def test_normalize_name_collapses_whitespace():
    assert normalize_name("Amul   Butter   500g") == "amul butter"


def test_normalize_name_strips_stopwords():
    assert normalize_name("Pack of Amul Butter") == "amul butter"
