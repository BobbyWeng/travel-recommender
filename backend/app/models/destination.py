from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Destination(Base):
    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="United States")
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
    iata_code: Mapped[str] = mapped_column(String(3), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)
    cost_level: Mapped[int] = mapped_column(Integer, nullable=False)
    public_transport_score: Mapped[int] = mapped_column(Integer, nullable=False)
    walkability_score: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    tags: Mapped[list["DestinationTag"]] = relationship(back_populates="destination", cascade="all, delete-orphan")
    monthly_climate: Mapped[list["DestinationMonthlyClimate"]] = relationship(
        back_populates="destination", cascade="all, delete-orphan"
    )


class DestinationTag(Base):
    __tablename__ = "destination_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    destination_id: Mapped[int] = mapped_column(Integer, ForeignKey("destinations.id"), nullable=False)
    tag: Mapped[str] = mapped_column(String(50), nullable=False)

    destination: Mapped["Destination"] = relationship(back_populates="tags")

    __table_args__ = (UniqueConstraint("destination_id", "tag"),)


class DestinationMonthlyClimate(Base):
    __tablename__ = "destination_monthly_climate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    destination_id: Mapped[int] = mapped_column(Integer, ForeignKey("destinations.id"), nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    temp_avg_c: Mapped[float | None] = mapped_column(Float)
    temp_max_avg_c: Mapped[float | None] = mapped_column(Float)
    temp_min_avg_c: Mapped[float | None] = mapped_column(Float)
    precip_days: Mapped[float | None] = mapped_column(Float)
    precip_mm: Mapped[float | None] = mapped_column(Float)
    sunshine_hours: Mapped[float | None] = mapped_column(Float)
    uv_index_avg: Mapped[float | None] = mapped_column(Float)
    wind_speed_avg_kmh: Mapped[float | None] = mapped_column(Float)

    destination: Mapped["Destination"] = relationship(back_populates="monthly_climate")

    __table_args__ = (UniqueConstraint("destination_id", "month"),)


class Airport(Base):
    __tablename__ = "airports"

    iata_code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    is_hub: Mapped[bool] = mapped_column(Boolean, default=False)


class FlightSearchCache(Base):
    __tablename__ = "flight_search_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_date: Mapped[date] = mapped_column(Date, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    stops: Mapped[int | None] = mapped_column(Integer)
    total_duration_min: Mapped[int | None] = mapped_column(Integer)
    airline: Mapped[str | None] = mapped_column(String(100))
    observed_at: Mapped[datetime] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    raw_response: Mapped[str | None] = mapped_column(Text)


class HotelSearchCache(Base):
    __tablename__ = "hotel_search_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    destination_iata: Mapped[str] = mapped_column(String(3), nullable=False)
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    nightly_price: Mapped[float | None] = mapped_column(Float)
    total_price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    hotel_class: Mapped[float | None] = mapped_column(Float)
    area: Mapped[str | None] = mapped_column(String(100))
    observed_at: Mapped[datetime] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    raw_response: Mapped[str | None] = mapped_column(Text)


class SearchRequest(Base):
    __tablename__ = "search_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    preferred_departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    date_flexibility_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trip_length_min: Mapped[int] = mapped_column(Integer, nullable=False)
    trip_length_max: Mapped[int] = mapped_column(Integer, nullable=False)
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    preferences: Mapped[str | None] = mapped_column(Text)
    constraints: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column()


class SearchCandidate(Base):
    __tablename__ = "search_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    search_id: Mapped[str] = mapped_column(String(36), ForeignKey("search_requests.id"), nullable=False)
    destination_id: Mapped[int] = mapped_column(Integer, ForeignKey("destinations.id"), nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_date: Mapped[date] = mapped_column(Date, nullable=False)
    flight_price: Mapped[float | None] = mapped_column(Float)
    hotel_price: Mapped[float | None] = mapped_column(Float)
    estimated_total: Mapped[float | None] = mapped_column(Float)
    flight_score: Mapped[float | None] = mapped_column(Float)
    hotel_score: Mapped[float | None] = mapped_column(Float)
    weather_score: Mapped[float | None] = mapped_column(Float)
    preference_score: Mapped[float | None] = mapped_column(Float)
    transport_score: Mapped[float | None] = mapped_column(Float)
    activity_score: Mapped[float | None] = mapped_column(Float)
    total_score: Mapped[float | None] = mapped_column(Float)
    passed_constraints: Mapped[bool | None] = mapped_column(Boolean)
    recommendation_reason: Mapped[str | None] = mapped_column(Text)
    warnings: Mapped[str | None] = mapped_column(Text)
