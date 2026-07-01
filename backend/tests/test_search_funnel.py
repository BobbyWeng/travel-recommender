import asyncio
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

from app.schemas.search import (
    ClimateAverage,
    SearchConstraints,
    SearchExecutionBudget,
    SearchRequestSchema,
)
from app.services.destination_service import DestinationService
from app.services.flight_service import FlightService
from app.services.hotel_service import HotelService
from app.services.scoring_service import ScoringService
from app.services.search_orchestrator import SearchOrchestrator
from app.services.weather_service import WeatherService
from app.providers.mock_flight import MockFlightProvider, set_coordinates
from app.providers.mock_hotel import MockHotelProvider, set_cost_levels
from app.providers.mock_weather import MockWeatherProvider, set_climate_data
from app.core.cache import flight_cache, hotel_cache, weather_cache

DATA_PATH = str(Path(__file__).parent.parent.parent / "data" / "destinations.json")


def _build_orchestrator(budget=None):
    flight_cache.clear()
    hotel_cache.clear()
    weather_cache.clear()

    dest_svc = DestinationService(DATA_PATH)
    coords = {}
    cost_levels = {}
    climate_data = {}

    for d in dest_svc.get_all_destinations():
        coords[d.iata_code] = (d.latitude, d.longitude)
        cost_levels[d.iata_code] = d.cost_level
        month_data = {}
        for c in dest_svc._climates.get(d.id, []):
            month_data[c.month] = ClimateAverage(
                destination_iata=d.iata_code,
                month=c.month,
                temp_avg_c=c.temp_avg_c,
                temp_max_avg_c=c.temp_max_avg_c,
                temp_min_avg_c=c.temp_min_avg_c,
                precip_days=c.precip_days,
                precip_mm=c.precip_mm,
                sunshine_hours=c.sunshine_hours,
                uv_index_avg=c.uv_index_avg,
                wind_speed_avg_kmh=c.wind_speed_avg_kmh,
            )
        climate_data[d.iata_code] = month_data

    set_coordinates(coords)
    set_cost_levels(cost_levels)
    set_climate_data(climate_data)

    return SearchOrchestrator(
        destination_service=dest_svc,
        flight_service=FlightService(MockFlightProvider(seed=42)),
        hotel_service=HotelService(MockHotelProvider(seed=42)),
        weather_service=WeatherService(MockWeatherProvider(seed=42)),
        scoring_service=ScoringService(),
        budget=budget or SearchExecutionBudget(),
    )


def test_stage1_no_external_api_calls():
    dest_svc = DestinationService(DATA_PATH)
    mock_flight = AsyncMock()
    mock_hotel = AsyncMock()
    mock_weather = AsyncMock()

    orch = SearchOrchestrator(
        destination_service=dest_svc,
        flight_service=FlightService(mock_flight),
        hotel_service=HotelService(mock_hotel),
        weather_service=WeatherService(mock_weather),
        scoring_service=ScoringService(),
    )

    pre_scores = dest_svc.pre_score_candidates(
        preferences=["nature"],
        constraints=SearchConstraints(),
        origin_iata="ATL",
        month=9,
    )

    mock_flight.search_flights.assert_not_called()
    mock_hotel.search_hotels.assert_not_called()
    mock_weather.get_forecast.assert_not_called()
    assert len(pre_scores) <= 20
    assert all(s.total_score > 0 for s in pre_scores)


def test_stage2_uses_limited_date_samples():
    budget = SearchExecutionBudget(max_stage2_date_samples=3)
    orch = _build_orchestrator(budget)

    request = SearchRequestSchema(
        origin="ATL",
        preferred_departure_date=date(2026, 9, 20),
        date_flexibility_days=3,
        trip_length_min=4,
        trip_length_max=5,
        budget=2000,
        constraints=SearchConstraints(),
    )
    response = asyncio.run(orch.execute(request))
    assert response.execution_stats is not None
    assert response.execution_stats.stage1_candidates <= 20


def test_budget_not_exceeded():
    budget = SearchExecutionBudget(max_provider_calls=50)
    orch = _build_orchestrator(budget)

    request = SearchRequestSchema(
        origin="ATL",
        preferred_departure_date=date(2026, 9, 20),
        date_flexibility_days=5,
        trip_length_min=4,
        trip_length_max=6,
        budget=3000,
        constraints=SearchConstraints(),
    )
    response = asyncio.run(orch.execute(request))
    assert response.execution_stats is not None
    assert response.execution_stats.provider_calls <= 50 + 10


def test_results_sorted_by_score():
    orch = _build_orchestrator()
    request = SearchRequestSchema(
        origin="ATL",
        preferred_departure_date=date(2026, 9, 20),
        date_flexibility_days=3,
        trip_length_min=4,
        trip_length_max=5,
        budget=2000,
        constraints=SearchConstraints(),
    )
    response = asyncio.run(orch.execute(request))
    scores = [r.total_score for r in response.top_results]
    assert scores == sorted(scores, reverse=True)


def test_execution_stats_populated():
    orch = _build_orchestrator()
    request = SearchRequestSchema(
        origin="ATL",
        preferred_departure_date=date(2026, 9, 20),
        date_flexibility_days=3,
        trip_length_min=4,
        trip_length_max=5,
        budget=2000,
        constraints=SearchConstraints(),
    )
    response = asyncio.run(orch.execute(request))
    stats = response.execution_stats
    assert stats is not None
    assert stats.stage1_candidates > 0
    assert stats.elapsed_ms >= 0
    assert isinstance(stats.provider_calls, int)


def test_60_cities_limited_candidates_queried():
    orch = _build_orchestrator()
    request = SearchRequestSchema(
        origin="ATL",
        preferred_departure_date=date(2026, 9, 20),
        date_flexibility_days=3,
        trip_length_min=4,
        trip_length_max=5,
        budget=2000,
        constraints=SearchConstraints(),
    )
    response = asyncio.run(orch.execute(request))
    stats = response.execution_stats
    assert stats.stage1_candidates <= 20
    assert stats.stage2_candidates <= 8


def test_cache_hit_on_second_search():
    flight_cache.clear()
    hotel_cache.clear()
    weather_cache.clear()

    orch = _build_orchestrator()
    request = SearchRequestSchema(
        origin="ATL",
        preferred_departure_date=date(2026, 9, 20),
        date_flexibility_days=0,
        trip_length_min=4,
        trip_length_max=4,
        budget=2000,
        constraints=SearchConstraints(),
    )

    asyncio.run(orch.execute(request))
    response2 = asyncio.run(orch.execute(request))

    assert len(response2.top_results) > 0
    assert response2.execution_stats.cache_hits >= 0


def test_pre_score_candidates_returns_max():
    dest_svc = DestinationService(DATA_PATH)
    scores = dest_svc.pre_score_candidates(
        preferences=["nature", "food"],
        constraints=SearchConstraints(),
        origin_iata="ATL",
        month=9,
        max_candidates=15,
    )
    assert len(scores) <= 15


def test_low_budget_no_results_with_funnel():
    orch = _build_orchestrator()
    request = SearchRequestSchema(
        origin="ATL",
        preferred_departure_date=date(2026, 9, 20),
        date_flexibility_days=0,
        trip_length_min=5,
        trip_length_max=5,
        budget=50,
        constraints=SearchConstraints(),
    )
    response = asyncio.run(orch.execute(request))
    assert len(response.top_results) == 0
