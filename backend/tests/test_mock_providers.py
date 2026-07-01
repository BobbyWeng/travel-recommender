import asyncio
from datetime import date

from app.schemas.search import FlightResult, HotelResult, WeatherResult
from app.providers.mock_flight import MockFlightProvider
from app.providers.mock_hotel import MockHotelProvider, set_cost_levels
from app.providers.mock_weather import MockWeatherProvider, set_climate_data
from app.schemas.search import ClimateAverage


def test_mock_flight_basic():
    set_cost_levels({"SFO": 5})
    provider = MockFlightProvider(seed=42)
    result = asyncio.run(provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25)))
    assert result is not None
    assert result.price > 0
    assert result.source == "mock"
    assert result.origin == "ATL"
    assert result.destination == "SFO"


def test_mock_flight_same_airport():
    provider = MockFlightProvider(seed=42)
    result = asyncio.run(provider.search_flights("ATL", "ATL", date(2026, 9, 20), date(2026, 9, 25)))
    assert result is None


def test_mock_flight_deterministic():
    provider1 = MockFlightProvider(seed=42)
    provider2 = MockFlightProvider(seed=42)
    r1 = asyncio.run(provider1.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25)))
    r2 = asyncio.run(provider2.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25)))
    assert r1.price == r2.price


def test_mock_flight_price_reasonable():
    provider = MockFlightProvider(seed=42)
    results = []
    for _ in range(10):
        r = asyncio.run(provider.search_flights("ATL", "ORD", date(2026, 9, 20), date(2026, 9, 25)))
        if r:
            results.append(r.price)
    if results:
        avg = sum(results) / len(results)
        assert 50 < avg < 800


def test_mock_hotel_basic():
    set_cost_levels({"SFO": 5})
    provider = MockHotelProvider(seed=42)
    result = asyncio.run(provider.search_hotels("SFO", date(2026, 9, 20), date(2026, 9, 25)))
    assert result is not None
    assert result.nightly_price > 0
    assert result.source == "mock"
    assert result.total_price == result.nightly_price * 5


def test_mock_hotel_invalid_dates():
    provider = MockHotelProvider(seed=42)
    result = asyncio.run(provider.search_hotels("SFO", date(2026, 9, 25), date(2026, 9, 20)))
    assert result is None


def test_mock_weather_basic():
    climate = ClimateAverage(
        destination_iata="ATL", month=9, temp_avg_c=24.0, temp_max_avg_c=29.5,
        temp_min_avg_c=18.0, precip_days=7.0, precip_mm=85.0,
        sunshine_hours=7.5, uv_index_avg=6, wind_speed_avg_kmh=12.0,
    )
    set_climate_data({"ATL": {9: climate}})
    provider = MockWeatherProvider(seed=42)
    provider.set_iata("ATL")
    result = asyncio.run(provider.get_forecast(33.75, -84.39, date(2026, 9, 20), date(2026, 9, 25)))
    assert len(result.days) == 6
    assert result.source == "mock"
    for day in result.days:
        assert 0 <= day.precip_probability <= 100


def test_mock_weather_no_climate_data():
    set_climate_data({})
    provider = MockWeatherProvider(seed=42)
    provider.set_iata("")
    result = asyncio.run(provider.get_forecast(33.75, -84.39, date(2026, 9, 20), date(2026, 9, 25)))
    assert len(result.days) == 6
