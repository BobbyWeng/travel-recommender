import asyncio
from datetime import date
from pathlib import Path

from app.schemas.search import SearchConstraints, SearchRequestSchema
from app.services.destination_service import DestinationService
from app.services.flight_service import FlightService
from app.services.hotel_service import HotelService
from app.services.scoring_service import ScoringService
from app.services.search_orchestrator import SearchOrchestrator
from app.services.weather_service import WeatherService
from app.providers.mock_flight import MockFlightProvider, set_coordinates
from app.providers.mock_hotel import MockHotelProvider, set_cost_levels
from app.providers.mock_weather import MockWeatherProvider, set_climate_data
from app.schemas.search import ClimateAverage
from app.core.cache import flight_cache, hotel_cache, weather_cache


DATA_PATH = str(Path(__file__).parent.parent.parent / "data" / "destinations.json")


def _build_orchestrator() -> SearchOrchestrator:
    flight_cache.clear()
    hotel_cache.clear()
    weather_cache.clear()

    dest_svc = DestinationService(DATA_PATH)
    coords: dict[str, tuple[float, float]] = {}
    cost_levels: dict[str, int] = {}
    climate_data: dict[str, dict[int, ClimateAverage]] = {}

    for d in dest_svc.get_all_destinations():
        coords[d.iata_code] = (d.latitude, d.longitude)
        cost_levels[d.iata_code] = d.cost_level
        month_data = {}
        for c in dest_svc._climates.get(d.id, []):
            month_data[c.month] = ClimateAverage(
                destination_iata=d.iata_code, month=c.month,
                temp_avg_c=c.temp_avg_c, temp_max_avg_c=c.temp_max_avg_c,
                temp_min_avg_c=c.temp_min_avg_c, precip_days=c.precip_days,
                precip_mm=c.precip_mm, sunshine_hours=c.sunshine_hours,
                uv_index_avg=c.uv_index_avg, wind_speed_avg_kmh=c.wind_speed_avg_kmh,
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
    )


def test_basic_search_returns_top5():
    orch = _build_orchestrator()
    request = SearchRequestSchema(
        origin="ATL",
        preferred_departure_date=date(2026, 9, 20),
        date_flexibility_days=5,
        trip_length_min=4,
        trip_length_max=6,
        budget=1500,
        preferences=["nature", "food"],
        constraints=SearchConstraints(max_flight_hours=8, max_stops=1),
    )
    response = asyncio.run(orch.execute(request))
    assert len(response.top_results) <= 5
    assert response.total_candidates_evaluated > 0


def test_search_results_have_scores():
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
    for r in response.top_results:
        assert 0 <= r.total_score <= 100
        assert r.flight_price > 0
        assert r.hotel_price > 0
        assert r.estimated_total <= 2000


def test_low_budget_no_results():
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


def test_avoid_hot_weather_filters():
    orch = _build_orchestrator()
    request = SearchRequestSchema(
        origin="ATL",
        preferred_departure_date=date(2026, 7, 20),
        date_flexibility_days=0,
        trip_length_min=5,
        trip_length_max=5,
        budget=3000,
        preferences=[],
        constraints=SearchConstraints(avoid_hot_weather=True),
    )
    response = asyncio.run(orch.execute(request))
    for r in response.top_results:
        assert r.weather_summary is not None


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


def test_search_results_data_source_is_mock():
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
    response = asyncio.run(orch.execute(request))
    assert response.data_source == "mock"
    for r in response.top_results:
        assert r.data_source == "mock"
