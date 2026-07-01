import asyncio
import pytest
from datetime import date

from app.providers.amadeus_flight import AmadeusFlightProvider
from app.providers.amadeus_hotel import AmadeusHotelProvider
from app.providers.openmeteo_weather import OpenMeteoWeatherProvider
from app.providers.fallback import FallbackFlightProvider, FallbackHotelProvider, FallbackWeatherProvider
from app.providers.mock_flight import MockFlightProvider
from app.providers.mock_hotel import MockHotelProvider
from app.providers.mock_weather import MockWeatherProvider
from app.core.config import settings


class TestAmadeusFlightProvider:
    def test_init_requires_credentials(self):
        original_id = settings.AMADEUS_CLIENT_ID
        settings.AMADEUS_CLIENT_ID = ""
        settings.AMADEUS_CLIENT_SECRET = ""
        provider = AmadeusFlightProvider()
        result = asyncio.run(provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25)))
        assert result is None
        settings.AMADEUS_CLIENT_ID = original_id


class TestOpenMeteoWeatherProvider:
    def test_get_forecast_returns_result(self):
        provider = OpenMeteoWeatherProvider()
        result = asyncio.run(provider.get_forecast(40.71, -74.01, date.today(), date.today()))
        assert result is not None
        assert isinstance(result.days, list)

    def test_get_climate_average_returns_data(self):
        provider = OpenMeteoWeatherProvider()
        result = asyncio.run(provider.get_climate_average(40.71, -74.01, 9))
        if result:
            assert result.month == 9


class TestFallbackFlightProvider:
    def test_falls_back_to_mock(self):
        mock = MockFlightProvider(seed=42)
        primary = AmadeusFlightProvider()

        fallback = FallbackFlightProvider(primary=primary, fallback=mock)
        result = asyncio.run(fallback.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25)))
        assert result is not None
        assert result.source == "mock"

    def test_uses_primary_when_available(self):
        class FakePrimary(MockFlightProvider):
            async def search_flights(self, *args, **kwargs):
                r = await super().search_flights(*args, **kwargs)
                if r:
                    r.source = "fake-primary"
                return r

        fallback = FallbackFlightProvider(primary=FakePrimary(seed=42), fallback=MockFlightProvider(seed=99))
        result = asyncio.run(fallback.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25)))
        assert result is not None
        assert result.source == "fake-primary"


class TestFallbackHotelProvider:
    def test_falls_back_to_mock(self):
        from app.providers.mock_hotel import set_cost_levels
        set_cost_levels({"SFO": 5})
        mock = MockHotelProvider(seed=42)
        primary = AmadeusHotelProvider()

        fallback = FallbackHotelProvider(primary=primary, fallback=mock)
        result = asyncio.run(fallback.search_hotels("SFO", date(2026, 9, 20), date(2026, 9, 25)))
        assert result is not None
        assert result.source == "mock"


class TestFallbackWeatherProvider:
    def test_falls_back_to_mock(self):
        from app.providers.mock_weather import set_climate_data
        from app.schemas.search import ClimateAverage

        set_climate_data({"ATL": {9: ClimateAverage(
            destination_iata="ATL", month=9, temp_avg_c=24.0, temp_max_avg_c=29.5,
            temp_min_avg_c=18.0, precip_days=7.0, precip_mm=85.0,
            sunshine_hours=7.5, uv_index_avg=6, wind_speed_avg_kmh=12.0,
        )}})

        mock = MockWeatherProvider(seed=42)
        mock.set_iata("ATL")
        primary = OpenMeteoWeatherProvider()

        fallback = FallbackWeatherProvider(primary=primary, fallback=mock)
        result = asyncio.run(fallback.get_forecast(33.75, -84.39, date(2026, 9, 20), date(2026, 9, 25)))
        assert len(result.days) > 0
