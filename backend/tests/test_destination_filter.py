import pytest
from pathlib import Path

from app.schemas.search import SearchConstraints
from app.services.destination_service import DestinationService


DATA_PATH = str(Path(__file__).parent.parent.parent / "data" / "destinations.json")


def test_load_data():
    svc = DestinationService(DATA_PATH)
    dests = svc.get_all_destinations()
    assert len(dests) == 20


def test_get_by_iata():
    svc = DestinationService(DATA_PATH)
    nyc = svc.get_by_iata("JFK")
    assert nyc is not None
    assert nyc.city == "New York"


def test_get_by_iata_not_found():
    svc = DestinationService(DATA_PATH)
    assert svc.get_by_iata("XXX") is None


def test_get_by_id():
    svc = DestinationService(DATA_PATH)
    d = svc.get_by_id(1)
    assert d is not None
    assert d.city == "New York"


def test_filter_domestic_only():
    svc = DestinationService(DATA_PATH)
    constraints = SearchConstraints(domestic_only=True)
    candidates = svc.filter_candidates([], constraints)
    for c in candidates:
        assert c.country_code == "US"


def test_filter_no_car_rental():
    svc = DestinationService(DATA_PATH)
    constraints = SearchConstraints(no_car_rental=True)
    candidates = svc.filter_candidates([], constraints)
    for c in candidates:
        assert c.public_transport_score >= 5


def test_filter_excludes_origin():
    svc = DestinationService(DATA_PATH)
    candidates = svc.filter_candidates([], SearchConstraints(), origin_iata="JFK")
    for c in candidates:
        assert c.iata_code != "JFK"


def test_filter_by_preferences():
    svc = DestinationService(DATA_PATH)
    candidates = svc.filter_candidates(["beach"], SearchConstraints())
    assert len(candidates) > 0
    for c in candidates:
        assert "beach" in c.tags


def test_climate_data_exists():
    svc = DestinationService(DATA_PATH)
    for d in svc.get_all_destinations():
        climate = svc.get_climate(d.id, 9)
        assert climate is not None, f"{d.city} 缺少 9 月气候数据"
        assert climate.temp_max_avg_c > -50


def test_all_have_12_months():
    svc = DestinationService(DATA_PATH)
    for d in svc.get_all_destinations():
        for month in range(1, 13):
            climate = svc.get_climate(d.id, month)
            assert climate is not None, f"{d.city} 缺少 {month} 月气候数据"
