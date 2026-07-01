from datetime import date

from pydantic import BaseModel, Field


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


class WeatherResult(BaseModel):
    destination_iata: str
    days: list[WeatherDay]
    source: str = "unknown"


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


class SearchResponse(BaseModel):
    request_id: str
    origin: str
    top_results: list[ScoredDestination]
    total_candidates_evaluated: int
    total_candidates_filtered: int
    data_source: str = "unknown"
    warnings: list[str] = Field(default_factory=list)
    llm_explanation: str = ""


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
