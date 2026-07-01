from dataclasses import dataclass
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


class SimpleCache:
    def __init__(self, default_ttl_hours: int = 4):
        self._store: dict[str, CacheEntry] = {}
        self._default_ttl_hours = default_ttl_hours

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry and entry.is_valid():
            return entry.data
        if entry:
            del self._store[key]
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

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)


flight_cache = SimpleCache(default_ttl_hours=4)
hotel_cache = SimpleCache(default_ttl_hours=4)
weather_cache = SimpleCache(default_ttl_hours=6)
