from __future__ import annotations

from datetime import date

from app.providers.base import FlightProvider
from app.schemas.search import DataKind, FlightResult, SourceMetadata
from app.core.cache import flight_cache
from app.core.db_cache import get_db_cache


class FlightService:
    def __init__(self, provider: FlightProvider):
        self._provider = provider

    async def search(
        self, origin: str, destination: str, depart_date: date, return_date: date
    ) -> FlightResult | None:
        cache_key = f"flight:{origin}:{destination}:{depart_date}:{return_date}:1:USD:eco"
        cached = flight_cache.get(cache_key)
        if cached is not None:
            if cached.source_metadata and not cached.source_metadata.cache_hit:
                cached.source_metadata.cache_hit = True
                if cached.source_metadata.data_kind == DataKind.LIVE:
                    cached.source_metadata.data_kind = DataKind.CACHED
            return cached

        db_cached = get_db_cache().get_flight_cache(origin, destination, depart_date, return_date)
        if db_cached is not None:
            result = self._db_cache_to_result(db_cached)
            flight_cache.set(cache_key, result)
            return result

        result = await self._provider.search_flights(origin, destination, depart_date, return_date)
        if result:
            flight_cache.set(cache_key, result)
            get_db_cache().set_flight_cache(
                origin=origin,
                destination=destination,
                depart_date=depart_date,
                return_date=return_date,
                provider=result.source,
                price=result.price,
                currency=result.currency,
                stops=result.stops,
                total_duration_min=result.total_duration_min,
                airline=result.airline,
            )
        return result

    @staticmethod
    def _db_cache_to_result(d: dict) -> FlightResult:
        return FlightResult(
            origin=d["origin"],
            destination=d["destination"],
            departure_date=date.fromisoformat(d["departure_date"]),
            return_date=date.fromisoformat(d["return_date"]),
            price=d["price"],
            currency=d.get("currency", "USD"),
            stops=d.get("stops", 0),
            total_duration_min=d.get("total_duration_min", 0),
            airline=d.get("airline"),
            source=d.get("provider", "cached"),
            source_metadata=SourceMetadata(
                provider=d.get("provider", "cached"),
                data_kind=DataKind.CACHED,
                cache_hit=True,
            ),
        )
