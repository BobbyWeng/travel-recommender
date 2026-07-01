from __future__ import annotations

import logging
from datetime import date

from app.core.config import settings
from app.providers.base import FlightProvider, HotelProvider, WeatherProvider
from app.providers.errors import ProviderError, ProviderErrorCode
from app.schemas.search import ClimateAverage, FlightResult, HotelResult, SourceMetadata, DataKind, WeatherResult

logger = logging.getLogger(__name__)


class FallbackFlightProvider(FlightProvider):
    def __init__(self, primary: FlightProvider, fallback: FlightProvider):
        self._primary = primary
        self._fallback = fallback

    async def search_flights(
        self, origin: str, destination: str, depart_date: date, return_date: date
    ) -> FlightResult | None:
        try:
            result = await self._primary.search_flights(origin, destination, depart_date, return_date)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"Primary flight provider failed: {e}")

        if not settings.ALLOW_MOCK_FALLBACK:
            logger.warning("Mock fallback disabled; returning None for flight search")
            return None

        logger.info("Falling back to mock flight provider")
        result = await self._fallback.search_flights(origin, destination, depart_date, return_date)
        if result:
            result.source = "mock"
            result.source_metadata = SourceMetadata(
                provider="mock",
                data_kind=DataKind.MOCK,
                fallback_used=True,
                fallback_reason="primary_provider_failed",
            )
        return result

    async def search_cheapest_dates(
        self, origin: str, destination: str, start_date: date, end_date: date
    ) -> list[FlightResult]:
        try:
            results = await self._primary.search_cheapest_dates(origin, destination, start_date, end_date)
            if results:
                return results
        except Exception as e:
            logger.warning(f"Primary flight provider failed: {e}")

        if not settings.ALLOW_MOCK_FALLBACK:
            logger.warning("Mock fallback disabled; returning empty list for cheapest dates")
            return []

        return await self._fallback.search_cheapest_dates(origin, destination, start_date, end_date)


class FallbackHotelProvider(HotelProvider):
    def __init__(self, primary: HotelProvider, fallback: HotelProvider):
        self._primary = primary
        self._fallback = fallback

    async def search_hotels(
        self, city_iata: str, check_in: date, check_out: date, adults: int = 2
    ) -> HotelResult | None:
        try:
            result = await self._primary.search_hotels(city_iata, check_in, check_out, adults)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"Primary hotel provider failed: {e}")

        if not settings.ALLOW_MOCK_FALLBACK:
            logger.warning("Mock fallback disabled; returning None for hotel search")
            return None

        logger.info("Falling back to mock hotel provider")
        result = await self._fallback.search_hotels(city_iata, check_in, check_out, adults)
        if result:
            result.source = "mock"
            result.source_metadata = SourceMetadata(
                provider="mock",
                data_kind=DataKind.MOCK,
                fallback_used=True,
                fallback_reason="primary_provider_failed",
            )
        return result


class FallbackWeatherProvider(WeatherProvider):
    def __init__(self, primary: WeatherProvider, fallback: WeatherProvider):
        self._primary = primary
        self._fallback = fallback

    async def get_forecast(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> WeatherResult:
        try:
            result = await self._primary.get_forecast(lat, lon, start_date, end_date)
            if result.days:
                return result
        except Exception as e:
            logger.warning(f"Primary weather provider failed: {e}")

        if not settings.ALLOW_MOCK_FALLBACK:
            logger.warning("Mock fallback disabled; returning empty weather result")
            return WeatherResult(destination_iata="", days=[], source="unavailable")

        logger.info("Falling back to mock weather provider")
        return await self._fallback.get_forecast(lat, lon, start_date, end_date)

    async def get_climate_average(self, lat: float, lon: float, month: int) -> ClimateAverage | None:
        try:
            result = await self._primary.get_climate_average(lat, lon, month)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"Primary weather climate failed: {e}")

        return await self._fallback.get_climate_average(lat, lon, month)
