from __future__ import annotations

from datetime import date

from app.providers.base import WeatherProvider
from app.providers.mock_weather import MockWeatherProvider
from app.schemas.search import ClimateAverage, WeatherResult
from app.core.cache import weather_cache


class WeatherService:
    def __init__(self, provider: WeatherProvider):
        self._provider = provider

    async def get_forecast(
        self, lat: float, lon: float, start_date: date, end_date: date, iata: str = ""
    ) -> WeatherResult:
        cache_key = f"weather:{iata}:{start_date}:{end_date}"
        cached = weather_cache.get(cache_key)
        if cached is not None:
            return cached

        if isinstance(self._provider, MockWeatherProvider):
            self._provider.set_iata(iata)

        result = await self._provider.get_forecast(lat, lon, start_date, end_date)
        result.destination_iata = iata
        weather_cache.set(cache_key, result)
        return result

    async def get_climate_average(self, lat: float, lon: float, month: int) -> ClimateAverage | None:
        return await self._provider.get_climate_average(lat, lon, month)
