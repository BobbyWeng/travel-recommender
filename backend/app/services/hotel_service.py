from __future__ import annotations

from datetime import date

from app.providers.base import HotelProvider
from app.schemas.search import HotelResult
from app.core.cache import hotel_cache
from app.core.db_cache import get_db_cache


class HotelService:
    def __init__(self, provider: HotelProvider):
        self._provider = provider

    async def search(
        self, city_iata: str, check_in: date, check_out: date, adults: int = 2
    ) -> HotelResult | None:
        cache_key = f"hotel:{city_iata}:{check_in}:{check_out}"
        cached = hotel_cache.get(cache_key)
        if cached is not None:
            return cached

        db_cached = get_db_cache().get_hotel_cache(city_iata, check_in, check_out)
        if db_cached is not None:
            result = self._db_cache_to_result(db_cached)
            hotel_cache.set(cache_key, result)
            return result

        result = await self._provider.search_hotels(city_iata, check_in, check_out, adults)
        if result:
            hotel_cache.set(cache_key, result)
            get_db_cache().set_hotel_cache(
                destination_iata=city_iata,
                check_in=check_in,
                check_out=check_out,
                provider=result.source,
                nightly_price=result.nightly_price,
                total_price=result.total_price,
                currency=result.currency,
                hotel_class=result.hotel_class,
                area=result.area,
            )
        return result

    @staticmethod
    def _db_cache_to_result(d: dict) -> HotelResult:
        return HotelResult(
            destination_iata=d["destination_iata"],
            check_in=date.fromisoformat(d["check_in"]),
            check_out=date.fromisoformat(d["check_out"]),
            nightly_price=d["nightly_price"],
            total_price=d["total_price"],
            currency=d.get("currency", "USD"),
            hotel_class=d.get("hotel_class", 3.0),
            area=d.get("area", ""),
            source=d.get("provider", "cached"),
        )
