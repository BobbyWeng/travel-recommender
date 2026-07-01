from __future__ import annotations

from datetime import date, timedelta

import httpx

from app.providers.base import WeatherProvider
from app.schemas.search import ClimateAverage, WeatherDay, WeatherResult


class OpenMeteoWeatherProvider(WeatherProvider):
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    async def get_forecast(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> WeatherResult:
        today = date.today()
        forecast_limit = today + timedelta(days=16)

        if start_date <= forecast_limit:
            return await self._get_real_forecast(lat, lon, start_date, end_date)
        else:
            return await self._get_climate_forecast(lat, lon, start_date, end_date)

    async def _get_real_forecast(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> WeatherResult:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max,uv_index_max,weather_code",
            "timezone": "auto",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(self.FORECAST_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, httpx.TimeoutException):
            return WeatherResult(destination_iata="", days=[], source="open-meteo-unavailable")

        return self._parse_daily_response(data, "open-meteo")

    async def _get_climate_forecast(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> WeatherResult:
        climate = await self.get_climate_average(lat, lon, start_date.month)
        if not climate:
            return WeatherResult(destination_iata="", days=[], source="open-meteo-climate-unavailable")

        days = []
        current = start_date
        while current <= end_date:
            days.append(
                WeatherDay(
                    date=current,
                    temp_max_c=climate.temp_max_avg_c,
                    temp_min_c=climate.temp_min_avg_c,
                    precip_probability=round((climate.precip_days / 30) * 100, 1),
                    precip_mm=round(climate.precip_mm / max(climate.precip_days, 1), 1),
                    wind_speed_kmh=climate.wind_speed_avg_kmh,
                    uv_index=climate.uv_index_avg,
                    weather_code=0,
                    source="open-meteo-climate",
                )
            )
            current += timedelta(days=1)

        return WeatherResult(destination_iata="", days=days, source="open-meteo-climate")

    async def get_climate_average(self, lat: float, lon: float, month: int) -> ClimateAverage | None:
        from app.services.destination_service import DestinationService
        from pathlib import Path

        data_path = Path(__file__).parent.parent.parent.parent / "data" / "destinations.json"
        if not data_path.exists():
            return None

        dest_svc = DestinationService(str(data_path))
        for d in dest_svc.get_all_destinations():
            if abs(d.latitude - lat) < 1.0 and abs(d.longitude - lon) < 1.0:
                climate = dest_svc.get_climate(d.id, month)
                if climate:
                    return ClimateAverage(
                        destination_iata=d.iata_code,
                        month=month,
                        temp_avg_c=climate.temp_avg_c,
                        temp_max_avg_c=climate.temp_max_avg_c,
                        temp_min_avg_c=climate.temp_min_avg_c,
                        precip_days=climate.precip_days,
                        precip_mm=climate.precip_mm,
                        sunshine_hours=climate.sunshine_hours,
                        uv_index_avg=climate.uv_index_avg,
                        wind_speed_avg_kmh=climate.wind_speed_avg_kmh,
                    )
        return None

    def _parse_daily_response(self, data: dict, source: str) -> WeatherResult:
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        temp_max = daily.get("temperature_2m_max", [])
        temp_min = daily.get("temperature_2m_min", [])
        precip_prob = daily.get("precipitation_probability_max", [])
        precip_sum = daily.get("precipitation_sum", [])
        wind_max = daily.get("wind_speed_10m_max", [])
        uv_max = daily.get("uv_index_max", [])
        weather_code = daily.get("weather_code", [])

        days = []
        for i in range(len(dates)):
            try:
                d = date.fromisoformat(dates[i])
            except (ValueError, IndexError):
                continue

            days.append(
                WeatherDay(
                    date=d,
                    temp_max_c=self._safe_float(temp_max, i),
                    temp_min_c=self._safe_float(temp_min, i),
                    precip_probability=self._safe_float(precip_prob, i),
                    precip_mm=self._safe_float(precip_sum, i),
                    wind_speed_kmh=self._safe_float(wind_max, i),
                    uv_index=self._safe_float(uv_max, i),
                    weather_code=self._safe_int(weather_code, i),
                    source=source,
                )
            )

        return WeatherResult(destination_iata="", days=days, source=source)

    @staticmethod
    def _safe_float(arr: list, idx: int) -> float:
        try:
            v = arr[idx]
            return round(float(v), 1) if v is not None else 0.0
        except (IndexError, TypeError, ValueError):
            return 0.0

    @staticmethod
    def _safe_int(arr: list, idx: int) -> int:
        try:
            v = arr[idx]
            return int(v) if v is not None else 0
        except (IndexError, TypeError, ValueError):
            return 0
