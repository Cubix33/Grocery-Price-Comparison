from app.server.cache import TTLCache, cache_key
import app.server.cache as cache_module


def test_cache_key_normalizes_case_and_whitespace():
    assert cache_key("Maggi", " Hostel Block A ") == cache_key("maggi", "hostel block a")


def test_returns_a_stored_value_before_it_expires():
    cache: TTLCache[str] = TTLCache(ttl_seconds=1000.0)
    cache.set("key", "value")
    assert cache.get("key") == "value"


def test_returns_none_after_ttl_elapses(monkeypatch):
    fake_time = {"now": 1000.0}
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: fake_time["now"])

    cache: TTLCache[str] = TTLCache(ttl_seconds=1.0)
    cache.set("key", "value")

    fake_time["now"] += 1.001

    assert cache.get("key") is None


def test_returns_none_for_a_key_that_was_never_set():
    cache: TTLCache[str] = TTLCache(ttl_seconds=1000.0)
    assert cache.get("missing") is None
