from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.destination import (
    FlightSearchCache,
    HotelSearchCache,
    Base,
)


class DBCacheService:
    def __init__(self, db_url: str | None = None):
        self._engine = create_engine(db_url or settings.DATABASE_URL, echo=False)

    def get_flight_cache(
        self, origin: str, destination: str, depart_date, return_date
    ) -> dict | None:
        with Session(self._engine) as session:
            row = (
                session.query(FlightSearchCache)
                .filter_by(
                    origin=origin,
                    destination=destination,
                    departure_date=depart_date,
                    return_date=return_date,
                )
                .first()
            )
            if row and row.expires_at and row.expires_at > datetime.utcnow():
                return self._flight_row_to_dict(row)
            if row:
                session.delete(row)
                session.commit()
        return None

    def set_flight_cache(
        self,
        origin: str,
        destination: str,
        depart_date,
        return_date,
        provider: str,
        price: float | None,
        currency: str = "USD",
        stops: int | None = None,
        total_duration_min: int | None = None,
        airline: str | None = None,
        raw_response: str | None = None,
        ttl_hours: int | None = None,
    ) -> None:
        ttl = ttl_hours or settings.CACHE_TTL_FLIGHT_HOURS
        now = datetime.utcnow()
        with Session(self._engine) as session:
            existing = (
                session.query(FlightSearchCache)
                .filter_by(
                    origin=origin,
                    destination=destination,
                    departure_date=depart_date,
                    return_date=return_date,
                    provider=provider,
                )
                .first()
            )
            if existing:
                existing.price = price
                existing.currency = currency
                existing.stops = stops
                existing.total_duration_min = total_duration_min
                existing.airline = airline
                existing.observed_at = now
                existing.expires_at = now + timedelta(hours=ttl)
                existing.raw_response = raw_response
            else:
                session.add(
                    FlightSearchCache(
                        origin=origin,
                        destination=destination,
                        departure_date=depart_date,
                        return_date=return_date,
                        provider=provider,
                        price=price,
                        currency=currency,
                        stops=stops,
                        total_duration_min=total_duration_min,
                        airline=airline,
                        observed_at=now,
                        expires_at=now + timedelta(hours=ttl),
                        raw_response=raw_response,
                    )
                )
            session.commit()

    def get_hotel_cache(
        self, destination_iata: str, check_in, check_out
    ) -> dict | None:
        with Session(self._engine) as session:
            row = (
                session.query(HotelSearchCache)
                .filter_by(
                    destination_iata=destination_iata,
                    check_in=check_in,
                    check_out=check_out,
                )
                .first()
            )
            if row and row.expires_at and row.expires_at > datetime.utcnow():
                return self._hotel_row_to_dict(row)
            if row:
                session.delete(row)
                session.commit()
        return None

    def set_hotel_cache(
        self,
        destination_iata: str,
        check_in,
        check_out,
        provider: str,
        nightly_price: float | None = None,
        total_price: float | None = None,
        currency: str = "USD",
        hotel_class: float | None = None,
        area: str | None = None,
        raw_response: str | None = None,
        ttl_hours: int | None = None,
    ) -> None:
        ttl = ttl_hours or settings.CACHE_TTL_HOTEL_HOURS
        now = datetime.utcnow()
        with Session(self._engine) as session:
            existing = (
                session.query(HotelSearchCache)
                .filter_by(
                    destination_iata=destination_iata,
                    check_in=check_in,
                    check_out=check_out,
                    provider=provider,
                )
                .first()
            )
            if existing:
                existing.nightly_price = nightly_price
                existing.total_price = total_price
                existing.currency = currency
                existing.hotel_class = hotel_class
                existing.area = area
                existing.observed_at = now
                existing.expires_at = now + timedelta(hours=ttl)
                existing.raw_response = raw_response
            else:
                session.add(
                    HotelSearchCache(
                        destination_iata=destination_iata,
                        check_in=check_in,
                        check_out=check_out,
                        provider=provider,
                        nightly_price=nightly_price,
                        total_price=total_price,
                        currency=currency,
                        hotel_class=hotel_class,
                        area=area,
                        observed_at=now,
                        expires_at=now + timedelta(hours=ttl),
                        raw_response=raw_response,
                    )
                )
            session.commit()

    def cleanup_expired(self) -> dict[str, int]:
        now = datetime.utcnow()
        counts = {"flights": 0, "hotels": 0}
        with Session(self._engine) as session:
            counts["flights"] = (
                session.query(FlightSearchCache).filter(FlightSearchCache.expires_at < now).delete()
            )
            counts["hotels"] = (
                session.query(HotelSearchCache).filter(HotelSearchCache.expires_at < now).delete()
            )
            session.commit()
        return counts

    def get_cache_stats(self) -> dict[str, Any]:
        now = datetime.utcnow()
        with Session(self._engine) as session:
            total_flights = session.query(FlightSearchCache).count()
            valid_flights = session.query(FlightSearchCache).filter(FlightSearchCache.expires_at > now).count()
            total_hotels = session.query(HotelSearchCache).count()
            valid_hotels = session.query(HotelSearchCache).filter(HotelSearchCache.expires_at > now).count()
        return {
            "flights": {"total": total_flights, "valid": valid_flights},
            "hotels": {"total": total_hotels, "valid": valid_hotels},
        }

    @staticmethod
    def _flight_row_to_dict(row: FlightSearchCache) -> dict:
        return {
            "origin": row.origin,
            "destination": row.destination,
            "departure_date": row.departure_date.isoformat(),
            "return_date": row.return_date.isoformat(),
            "provider": row.provider,
            "price": row.price,
            "currency": row.currency,
            "stops": row.stops,
            "total_duration_min": row.total_duration_min,
            "airline": row.airline,
            "source": row.provider,
        }

    @staticmethod
    def _hotel_row_to_dict(row: HotelSearchCache) -> dict:
        return {
            "destination_iata": row.destination_iata,
            "check_in": row.check_in.isoformat(),
            "check_out": row.check_out.isoformat(),
            "provider": row.provider,
            "nightly_price": row.nightly_price,
            "total_price": row.total_price,
            "currency": row.currency,
            "hotel_class": row.hotel_class,
            "area": row.area,
            "source": row.provider,
        }


_db_cache: DBCacheService | None = None


def get_db_cache() -> DBCacheService:
    global _db_cache
    if _db_cache is None:
        _db_cache = DBCacheService()
    return _db_cache
