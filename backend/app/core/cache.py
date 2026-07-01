from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class CacheEntry:
    key: str
    data: Any
    observed_at: datetime
    expires_at: datetime

    def is_valid(self) -> bool:
        return datetime.utcnow() < self.expires_at


@dataclass
class CacheStats:
    hit: int = 0
    miss: int = 0
    set: int = 0
    expired: int = 0
    size: int = 0


class SimpleCache:
    def __init__(self, default_ttl_hours: int = 4):
        self._store: dict[str, CacheEntry] = {}
        self._default_ttl_hours = default_ttl_hours
        self._stats: CacheStats = CacheStats()

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry and entry.is_valid():
            self._stats.hit += 1
            return entry.data
        if entry:
            self._stats.expired += 1
            del self._store[key]
        self._stats.miss += 1
        return None

    def set(self, key: str, data: Any, ttl_hours: int | None = None) -> None:
        ttl = ttl_hours or self._default_ttl_hours
        now = datetime.utcnow()
        self._store[key] = CacheEntry(
            key=key,
            data=data,
            observed_at=now,
            expires_at=now + timedelta(hours=ttl),
        )
        self._stats.set += 1

    def clear(self) -> None:
        self._store.clear()
        self._stats = CacheStats()

    def size(self) -> int:
        return len(self._store)

    def get_stats(self) -> CacheStats:
        self._stats.size = len(self._store)
        return self._stats


flight_cache = SimpleCache(default_ttl_hours=4)
hotel_cache = SimpleCache(default_ttl_hours=4)
weather_cache = SimpleCache(default_ttl_hours=6)
