from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class DataKind(str, Enum):
    LIVE = "LIVE"
    CACHED = "CACHED"
    HISTORICAL = "HISTORICAL"
    ESTIMATED = "ESTIMATED"
    MOCK = "MOCK"
    UNAVAILABLE = "UNAVAILABLE"


class SourceMetadata(BaseModel):
    provider: str
    data_kind: DataKind
    fetched_at: datetime | None = None
    expires_at: datetime | None = None
    cache_hit: bool = False
    fallback_used: bool = False
    fallback_reason: str | None = None


class DataQualitySummary(BaseModel):
    completeness: float = 0.0
    live_field_count: int = 0
    cached_field_count: int = 0
    historical_field_count: int = 0
    estimated_field_count: int = 0
    mock_field_count: int = 0
    unavailable_field_count: int = 0


class SearchConstraints(BaseModel):
    max_flight_hours: int | None = Field(default=None, ge=1, le=30)
    max_stops: int | None = Field(default=None, ge=0, le=3)
    avoid_hot_weather: bool = False
    avoid_cold_weather: bool = False
    no_car_rental: bool = False
    domestic_only: bool = True


class SearchRequestSchema(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3, description="出发机场 IATA 代码")
    preferred_departure_date: date = Field(..., description="首选出发日期")
    date_flexibility_days: int = Field(default=0, ge=0, le=14, description="日期浮动天数")
    trip_length_min: int = Field(..., ge=1, le=30, description="最短旅行天数")
    trip_length_max: int = Field(..., ge=1, le=30, description="最长旅行天数")
    budget: float = Field(..., gt=0, description="总预算（USD）")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    preferences: list[str] = Field(default_factory=list, description="旅行偏好标签")
    constraints: SearchConstraints = Field(default_factory=SearchConstraints)


class DateCombo(BaseModel):
    departure_date: date
    return_date: date
    nights: int


class FlightSegment(BaseModel):
    origin: str
    destination: str
    departing_at: datetime
    arriving_at: datetime
    duration_minutes: int
    marketing_carrier: str | None = None
    operating_carrier: str | None = None
    flight_number: str | None = None


class FlightSlice(BaseModel):
    segments: list[FlightSegment]
    duration_minutes: int
    stops: int


class FlightOffer(BaseModel):
    provider: str
    provider_offer_id: str | None = None
    origin: str
    destination: str
    departure_date: date
    return_date: date | None = None
    outbound: FlightSlice | None = None
    inbound: FlightSlice | None = None
    total_price: Decimal = Decimal("0")
    currency: str = "USD"
    airlines: list[str] = []
    baggage_summary: str | None = None
    expires_at: datetime | None = None
    fetched_at: datetime | None = None
    source: SourceMetadata | None = None


class FlightResult(BaseModel):
    origin: str
    destination: str
    departure_date: date
    return_date: date
    price: float
    currency: str = "USD"
    stops: int
    total_duration_min: int
    airline: str | None = None
    source: str = "unknown"
    source_metadata: SourceMetadata | None = None
    offer: FlightOffer | None = None


class HotelResult(BaseModel):
    destination_iata: str
    check_in: date
    check_out: date
    nightly_price: float
    total_price: float
    currency: str = "USD"
    hotel_class: float = 3.0
    area: str = "downtown"
    source: str = "unknown"
    source_metadata: SourceMetadata | None = None


class WeatherDay(BaseModel):
    date: date
    temp_max_c: float
    temp_min_c: float
    precip_probability: float
    precip_mm: float
    wind_speed_kmh: float
    uv_index: float
    weather_code: int
    source: str = "unknown"
    source_metadata: SourceMetadata | None = None


class WeatherResult(BaseModel):
    destination_iata: str
    days: list[WeatherDay]
    source: str = "unknown"
    source_metadata: SourceMetadata | None = None


class ClimateAverage(BaseModel):
    destination_iata: str
    month: int
    temp_avg_c: float
    temp_max_avg_c: float
    temp_min_avg_c: float
    precip_days: float
    precip_mm: float
    sunshine_hours: float
    uv_index_avg: float
    wind_speed_avg_kmh: float


class ScoreBreakdown(BaseModel):
    flight: float = Field(ge=0, le=100)
    hotel: float = Field(ge=0, le=100)
    weather: float = Field(ge=0, le=100)
    preference_match: float = Field(ge=0, le=100)
    transport: float = Field(ge=0, le=100)
    activities: float = Field(ge=0, le=100)


class CandidatePreScore(BaseModel):
    destination_id: int
    climate_score: float = 0.0
    preference_score: float = 0.0
    transport_score: float = 0.0
    affordability_score: float = 0.0
    distance_score: float = 0.0
    total_score: float = 0.0
    filtered_reason: str | None = None


class SearchExecutionBudget(BaseModel):
    max_provider_calls: int = 600
    max_stage1_candidates: int = 15
    max_stage2_candidates: int = 8
    max_stage2_date_samples: int = 3
    max_concurrency: int = 8


class SearchExecutionStats(BaseModel):
    stage1_candidates: int = 0
    stage2_candidates: int = 0
    stage3_candidates: int = 0
    provider_calls: int = 0
    cache_hits: int = 0
    provider_failures: int = 0
    fallback_count: int = 0
    elapsed_ms: int = 0
    budget_exhausted: bool = False


class ScoredDestination(BaseModel):
    destination_id: int
    city: str
    state: str
    iata_code: str
    departure_date: date
    return_date: date
    nights: int
    flight_price: float
    hotel_price: float
    estimated_total: float
    currency: str = "USD"
    weather_summary: str
    total_score: float = Field(ge=0, le=100)
    scores: ScoreBreakdown
    pros: list[str]
    cons: list[str]
    recommendation_reason: str
    data_source: str = "unknown"
    source_metadata: SourceMetadata | None = None
    flight_data_kind: DataKind | None = None
    hotel_data_kind: DataKind | None = None
    weather_data_kind: DataKind | None = None
    data_quality: DataQualitySummary | None = None


class SearchResponse(BaseModel):
    request_id: str
    origin: str
    top_results: list[ScoredDestination]
    total_candidates_evaluated: int
    total_candidates_filtered: int
    data_source: str = "unknown"
    warnings: list[str] = Field(default_factory=list)
    llm_explanation: str = ""
    execution_stats: SearchExecutionStats | None = None


class NaturalLanguageSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="自然语言搜索描述")


class NaturalLanguageSearchResponse(BaseModel):
    parsed_request: SearchRequestSchema | None = None
    search_response: SearchResponse | None = None
    llm_explanation: str = ""
    parse_error: str = ""


class TravelAdviceRequest(BaseModel):
    destination_id: int
    preferences: list[str] = Field(default_factory=list)


class TravelAdviceResponse(BaseModel):
    destination_id: int
    city: str
    state: str
    advice: str
