from __future__ import annotations

import os
import tempfile
from datetime import date, datetime, timedelta

import pytest

from app.core.db_cache import DBCacheService
from app.models.destination import Base, FlightSearchCache, HotelSearchCache
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def db_cache():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_url = f"sqlite:///{f.name}"
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    cache = DBCacheService(db_url=db_url)
    yield cache
    os.unlink(f.name)


class TestFlightCache:
    def test_set_and_get(self, db_cache):
        result = db_cache.get_flight_cache("ATL", "JFK", date(2026, 9, 20), date(2026, 9, 25))
        assert result is None

        db_cache.set_flight_cache(
            origin="ATL",
            destination="JFK",
            depart_date=date(2026, 9, 20),
            return_date=date(2026, 9, 25),
            provider="amadeus",
            price=350.0,
            currency="USD",
            stops=0,
            total_duration_min=180,
            airline="Delta",
        )

        result = db_cache.get_flight_cache("ATL", "JFK", date(2026, 9, 20), date(2026, 9, 25))
        assert result is not None
        assert result["origin"] == "ATL"
        assert result["destination"] == "JFK"
        assert result["price"] == 350.0
        assert result["provider"] == "amadeus"
        assert result["stops"] == 0

    def test_update_existing(self, db_cache):
        db_cache.set_flight_cache(
            origin="ATL", destination="JFK",
            depart_date=date(2026, 9, 20), return_date=date(2026, 9, 25),
            provider="amadeus", price=350.0,
        )
        db_cache.set_flight_cache(
            origin="ATL", destination="JFK",
            depart_date=date(2026, 9, 20), return_date=date(2026, 9, 25),
            provider="amadeus", price=320.0,
        )
        result = db_cache.get_flight_cache("ATL", "JFK", date(2026, 9, 20), date(2026, 9, 25))
        assert result["price"] == 320.0

    def test_expired_not_returned(self, db_cache):
        db_cache.set_flight_cache(
            origin="ATL", destination="JFK",
            depart_date=date(2026, 9, 20), return_date=date(2026, 9, 25),
            provider="amadeus", price=350.0,
            ttl_hours=-1,
        )
        result = db_cache.get_flight_cache("ATL", "JFK", date(2026, 9, 20), date(2026, 9, 25))
        assert result is None

    def test_different_routes_independent(self, db_cache):
        db_cache.set_flight_cache(
            origin="ATL", destination="JFK",
            depart_date=date(2026, 9, 20), return_date=date(2026, 9, 25),
            provider="amadeus", price=350.0,
        )
        db_cache.set_flight_cache(
            origin="ATL", destination="LAX",
            depart_date=date(2026, 9, 20), return_date=date(2026, 9, 25),
            provider="amadeus", price=400.0,
        )
        r1 = db_cache.get_flight_cache("ATL", "JFK", date(2026, 9, 20), date(2026, 9, 25))
        r2 = db_cache.get_flight_cache("ATL", "LAX", date(2026, 9, 20), date(2026, 9, 25))
        assert r1["price"] == 350.0
        assert r2["price"] == 400.0


class TestHotelCache:
    def test_set_and_get(self, db_cache):
        result = db_cache.get_hotel_cache("JFK", date(2026, 9, 20), date(2026, 9, 25))
        assert result is None

        db_cache.set_hotel_cache(
            destination_iata="JFK",
            check_in=date(2026, 9, 20),
            check_out=date(2026, 9, 25),
            provider="amadeus",
            nightly_price=200.0,
            total_price=1000.0,
            currency="USD",
            hotel_class=3.5,
            area="downtown",
        )

        result = db_cache.get_hotel_cache("JFK", date(2026, 9, 20), date(2026, 9, 25))
        assert result is not None
        assert result["destination_iata"] == "JFK"
        assert result["nightly_price"] == 200.0
        assert result["total_price"] == 1000.0
        assert result["provider"] == "amadeus"

    def test_expired_not_returned(self, db_cache):
        db_cache.set_hotel_cache(
            destination_iata="JFK",
            check_in=date(2026, 9, 20),
            check_out=date(2026, 9, 25),
            provider="amadeus",
            nightly_price=200.0,
            total_price=1000.0,
            ttl_hours=-1,
        )
        result = db_cache.get_hotel_cache("JFK", date(2026, 9, 20), date(2026, 9, 25))
        assert result is None


class TestCacheStats:
    def test_stats_empty(self, db_cache):
        stats = db_cache.get_cache_stats()
        assert stats["flights"]["total"] == 0
        assert stats["hotels"]["total"] == 0

    def test_stats_with_data(self, db_cache):
        db_cache.set_flight_cache(
            origin="ATL", destination="JFK",
            depart_date=date(2026, 9, 20), return_date=date(2026, 9, 25),
            provider="mock", price=350.0,
        )
        db_cache.set_hotel_cache(
            destination_iata="JFK",
            check_in=date(2026, 9, 20), check_out=date(2026, 9, 25),
            provider="mock", nightly_price=200.0, total_price=1000.0,
        )
        stats = db_cache.get_cache_stats()
        assert stats["flights"]["total"] == 1
        assert stats["flights"]["valid"] == 1
        assert stats["hotels"]["total"] == 1
        assert stats["hotels"]["valid"] == 1


class TestCacheCleanup:
    def test_cleanup_expired(self, db_cache):
        db_cache.set_flight_cache(
            origin="ATL", destination="JFK",
            depart_date=date(2026, 9, 20), return_date=date(2026, 9, 25),
            provider="mock", price=350.0, ttl_hours=-1,
        )
        db_cache.set_hotel_cache(
            destination_iata="JFK",
            check_in=date(2026, 9, 20), check_out=date(2026, 9, 25),
            provider="mock", nightly_price=200.0, total_price=1000.0, ttl_hours=-1,
        )
        counts = db_cache.cleanup_expired()
        assert counts["flights"] == 1
        assert counts["hotels"] == 1
