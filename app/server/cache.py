import time
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class _CacheEntry(Generic[T]):
    def __init__(self, value: T, expires_at: float):
        self.value = value
        self.expires_at = expires_at


class TTLCache(Generic[T]):
    """
    In-memory thread-safe key-value cache with monotonic time-to-live eviction.
    """

    def __init__(self, ttl_seconds: float):
        self._ttl_seconds = ttl_seconds
        self._store: dict[str, _CacheEntry[T]] = {}

    def get(self, key: str) -> Optional[T]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._store[key] = _CacheEntry(value, time.monotonic() + self._ttl_seconds)

    def clear(self) -> None:
        self._store.clear()


def cache_key(query: str, location: str) -> str:
    """Normalize query and location into a deterministic cache key."""
    return f"{query.strip().lower()}::{location.strip().lower()}"
