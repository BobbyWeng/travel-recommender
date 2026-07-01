from datetime import date

from app.schemas.search import (
    FlightResult,
    HotelResult,
    ScoreBreakdown,
    SearchConstraints,
    WeatherDay,
    WeatherResult,
)
from app.services.destination_service import DestinationInfo
from app.services.scoring_service import ScoringService


def _make_dest(**kwargs) -> DestinationInfo:
    defaults = dict(
        id=1, city="Test", state="TS", country="United States", country_code="US",
        iata_code="TST", latitude=40.0, longitude=-74.0, timezone="America/New_York",
        cost_level=3, public_transport_score=7, walkability_score=7,
        tags=["nature", "food", "city"],
    )
    defaults.update(kwargs)
    return DestinationInfo(**defaults)


def _make_flight(price=200, stops=0, duration=180) -> FlightResult:
    return FlightResult(
        origin="ATL", destination="TST",
        departure_date=date(2026, 9, 20), return_date=date(2026, 9, 25),
        price=price, stops=stops, total_duration_min=duration,
        airline="TestAir", source="mock",
    )


def _make_hotel(total=500, nightly=100) -> HotelResult:
    return HotelResult(
        destination_iata="TST", check_in=date(2026, 9, 20), check_out=date(2026, 9, 25),
        nightly_price=nightly, total_price=total,
        source="mock",
    )


def _make_weather(max_temps=None, min_temps=None, precip_probs=None) -> WeatherResult:
    n = len(max_temps) if max_temps else 5
    max_temps = max_temps or [25.0] * n
    min_temps = min_temps or [15.0] * n
    precip_probs = precip_probs or [20.0] * n
    days = []
    for i in range(n):
        days.append(WeatherDay(
            date=date(2026, 9, 20 + i),
            temp_max_c=max_temps[i], temp_min_c=min_temps[i],
            precip_probability=precip_probs[i], precip_mm=1.0,
            wind_speed_kmh=10.0, uv_index=5.0, weather_code=0, source="mock",
        ))
    return WeatherResult(destination_iata="TST", days=days, source="mock")


def test_flight_score_budget():
    s = ScoringService()
    assert s.score_flight(300, 1500) == 100
    assert s.score_flight(600, 1500) == 100  # 0.4 <= 0.4 → 100
    assert s.score_flight(900, 1500) == 90   # 0.6 <= 0.6 → 90
    assert s.score_flight(1200, 1500) == 70  # 0.8 <= 0.8 → 70
    assert s.score_flight(1500, 1500) == 50
    assert s.score_flight(2000, 1500) < 50


def test_hotel_score():
    s = ScoringService()
    score = s.score_hotel(300, 1500, 200)
    assert 0 <= score <= 100


def test_weather_score_comfortable():
    s = ScoringService()
    weather = _make_weather(max_temps=[24] * 5, min_temps=[16] * 5, precip_probs=[15] * 5)
    score = s.score_weather(weather, SearchConstraints())
    assert score >= 80


def test_weather_score_hot_avoided():
    s = ScoringService()
    weather = _make_weather(max_temps=[38] * 5, precip_probs=[10] * 5)
    score = s.score_weather(weather, SearchConstraints(avoid_hot_weather=True))
    assert score <= 50


def test_weather_score_cold_avoided():
    s = ScoringService()
    weather = _make_weather(min_temps=[-5] * 5, max_temps=[5] * 5, precip_probs=[10] * 5)
    score = s.score_weather(weather, SearchConstraints(avoid_cold_weather=True))
    assert score < 70


def test_preference_match():
    s = ScoringService()
    dest = _make_dest(tags=["nature", "food", "city"])
    score = s.score_preference_match(dest, ["nature", "food"])
    assert score >= 50
    score_no_match = s.score_preference_match(dest, ["beach", "skiing"])
    assert score_no_match < score


def test_transport_no_car_rental():
    s = ScoringService()
    dest_good = _make_dest(public_transport_score=8)
    dest_bad = _make_dest(public_transport_score=3)
    score_good = s.score_transport(dest_good, SearchConstraints(no_car_rental=True))
    score_bad = s.score_transport(dest_bad, SearchConstraints(no_car_rental=True))
    assert score_good > score_bad


def test_total_score_weights():
    s = ScoringService()
    breakdown = ScoreBreakdown(flight=80, hotel=70, weather=90, preference_match=60, transport=50, activities=40)
    total = s.compute_total_score(breakdown)
    expected = 80 * 0.30 + 70 * 0.20 + 90 * 0.20 + 60 * 0.15 + 50 * 0.10 + 40 * 0.05
    assert abs(total - expected) < 0.1


def test_hard_constraints_budget():
    s = ScoringService()
    flight = _make_flight(price=1200)
    hotel = _make_hotel(total=500)
    dest = _make_dest(public_transport_score=7)
    passed, warnings = s.check_hard_constraints(flight, hotel, None, dest, 1500, SearchConstraints())
    assert not passed
    assert any("超出预算" in w for w in warnings)


def test_hard_constraints_flight_hours():
    s = ScoringService()
    flight = _make_flight(duration=600)
    hotel = _make_hotel()
    dest = _make_dest(public_transport_score=7)
    passed, warnings = s.check_hard_constraints(flight, hotel, None, dest, 1500, SearchConstraints(max_flight_hours=8))
    assert not passed


def test_hard_constraints_stops():
    s = ScoringService()
    flight = _make_flight(stops=2)
    hotel = _make_hotel()
    dest = _make_dest(public_transport_score=7)
    passed, warnings = s.check_hard_constraints(flight, hotel, None, dest, 1500, SearchConstraints(max_stops=1))
    assert not passed


def test_hard_constraints_hot_weather():
    s = ScoringService()
    flight = _make_flight()
    hotel = _make_hotel()
    weather = _make_weather(max_temps=[40] * 5)
    dest = _make_dest(public_transport_score=7)
    passed, warnings = s.check_hard_constraints(flight, hotel, weather, dest, 1500, SearchConstraints(avoid_hot_weather=True))
    assert not passed


def test_hard_constraints_no_car():
    s = ScoringService()
    flight = _make_flight()
    hotel = _make_hotel()
    dest = _make_dest(public_transport_score=3)
    passed, warnings = s.check_hard_constraints(flight, hotel, None, dest, 1500, SearchConstraints(no_car_rental=True))
    assert not passed


def test_hard_constraints_pass():
    s = ScoringService()
    flight = _make_flight(price=300)
    hotel = _make_hotel(total=400)
    weather = _make_weather(max_temps=[25] * 5)
    dest = _make_dest(public_transport_score=7)
    passed, warnings = s.check_hard_constraints(
        flight, hotel, weather, dest, 1500,
        SearchConstraints(avoid_hot_weather=True, no_car_rental=True),
    )
    assert passed


def test_pros_cons_reason():
    s = ScoringService()
    dest = _make_dest(tags=["nature", "food"], public_transport_score=8)
    flight = _make_flight(price=300)
    hotel = _make_hotel(total=400)
    weather = _make_weather(max_temps=[25] * 5)
    breakdown = ScoreBreakdown(flight=90, hotel=85, weather=85, preference_match=80, transport=80, activities=70)
    pros, cons, reason = s.generate_pros_cons_reason(dest, flight, hotel, weather, breakdown, ["nature", "food"], 1500)
    assert any("nature" in p or "food" in p for p in pros)
    assert len(reason) > 0
