import random
from datetime import date, timedelta

from app.core.config import settings
from app.providers.base import WeatherProvider
from app.schemas.search import ClimateAverage, WeatherDay, WeatherResult

_CLIMATE_DATA: dict[str, dict[int, ClimateAverage]] = {}


def set_climate_data(data: dict[str, dict[int, ClimateAverage]]) -> None:
    _CLIMATE_DATA.update(data)


class MockWeatherProvider(WeatherProvider):
    def __init__(self, seed: int | None = None):
        self._rng = random.Random((seed or settings.MOCK_SEED) + 2)
        self._current_iata = ""

    def set_iata(self, iata: str) -> None:
        self._current_iata = iata

    async def get_forecast(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> WeatherResult:
        iata = self._current_iata
        days = []
        current = start_date
        while current <= end_date:
            climate = self._get_climate_for_iata(iata, current.month)
            if climate:
                temp_max = climate.temp_max_avg_c + self._rng.uniform(-3, 3)
                temp_min = climate.temp_min_avg_c + self._rng.uniform(-2, 2)
                precip_prob = min(95, (climate.precip_days / 30) * 100 + self._rng.uniform(-15, 15))
                precip_mm = climate.precip_mm / max(climate.precip_days, 1) if self._rng.random() < precip_prob / 100 else 0
                wind = climate.wind_speed_avg_kmh + self._rng.uniform(-3, 3)
                uv = climate.uv_index_avg + self._rng.uniform(-1, 1)
            else:
                temp_max = 22 + self._rng.uniform(-8, 8)
                temp_min = temp_max - 8 + self._rng.uniform(-3, 3)
                precip_prob = self._rng.uniform(5, 40)
                precip_mm = self._rng.uniform(0, 5) if self._rng.random() < precip_prob / 100 else 0
                wind = self._rng.uniform(5, 20)
                uv = self._rng.uniform(2, 8)

            weather_code = self._weather_code(precip_prob, precip_mm)

            days.append(
                WeatherDay(
                    date=current,
                    temp_max_c=round(temp_max, 1),
                    temp_min_c=round(temp_min, 1),
                    precip_probability=round(max(0, min(100, precip_prob)), 1),
                    precip_mm=round(max(0, precip_mm), 1),
                    wind_speed_kmh=round(max(0, wind), 1),
                    uv_index=round(max(0, uv), 1),
                    weather_code=weather_code,
                    source="mock",
                )
            )
            current += timedelta(days=1)

        return WeatherResult(
            destination_iata=iata,
            days=days,
            source="mock",
        )

    async def get_climate_average(self, lat: float, lon: float, month: int) -> ClimateAverage | None:
        if self._current_iata and self._current_iata in _CLIMATE_DATA:
            return _CLIMATE_DATA[self._current_iata].get(month)
        for city_data in _CLIMATE_DATA.values():
            if month in city_data:
                return city_data[month]
        return None

    def _get_climate_for_iata(self, iata: str, month: int) -> ClimateAverage | None:
        if iata and iata in _CLIMATE_DATA:
            return _CLIMATE_DATA[iata].get(month)
        for city_data in _CLIMATE_DATA.values():
            if month in city_data:
                return city_data[month]
        return None

    def _weather_code(self, precip_prob: float, precip_mm: float) -> int:
        if precip_mm > 10:
            return 61
        if precip_mm > 2:
            return 51
        if precip_prob > 60:
            return 3
        if precip_prob > 30:
            return 2
        return 0
