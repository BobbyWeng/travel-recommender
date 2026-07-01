export type DataKind = "LIVE" | "CACHED" | "HISTORICAL" | "ESTIMATED" | "MOCK" | "UNAVAILABLE";

export interface SourceMetadata {
  provider: string;
  data_kind: DataKind;
  fetched_at: string | null;
  expires_at: string | null;
  cache_hit: boolean;
  fallback_used: boolean;
  fallback_reason: string | null;
}

export interface DataQualitySummary {
  completeness: number;
  live_field_count: number;
  cached_field_count: number;
  historical_field_count: number;
  estimated_field_count: number;
  mock_field_count: number;
  unavailable_field_count: number;
}

export interface SearchExecutionStats {
  stage1_candidates: number;
  stage2_candidates: number;
  stage3_candidates: number;
  provider_calls: number;
  cache_hits: number;
  provider_failures: number;
  fallback_count: number;
  elapsed_ms: number;
  budget_exhausted: boolean;
}

export interface APIError {
  status?: number;
  code?: string;
  message: string;
  detail?: string;
}

export interface SearchConstraints {
  max_flight_hours?: number | null;
  max_stops?: number | null;
  avoid_hot_weather?: boolean;
  avoid_cold_weather?: boolean;
  no_car_rental?: boolean;
  domestic_only?: boolean;
}

export interface SearchRequest {
  origin: string;
  preferred_departure_date: string;
  date_flexibility_days: number;
  trip_length_min: number;
  trip_length_max: number;
  budget: number;
  currency: string;
  preferences: string[];
  constraints: SearchConstraints;
}

export interface ScoreBreakdown {
  flight: number;
  hotel: number;
  weather: number;
  preference_match: number;
  transport: number;
  activities: number;
}

export interface ScoredDestination {
  destination_id: number;
  city: string;
  state: string;
  iata_code: string;
  departure_date: string;
  return_date: string;
  nights: number;
  flight_price: number;
  hotel_price: number;
  estimated_total: number;
  currency: string;
  weather_summary: string;
  total_score: number;
  scores: ScoreBreakdown;
  pros: string[];
  cons: string[];
  recommendation_reason: string;
  data_source: string;
  flight_data_kind: DataKind | null;
  hotel_data_kind: DataKind | null;
  weather_data_kind: DataKind | null;
  data_quality: DataQualitySummary | null;
}

export interface SearchResponse {
  request_id: string;
  origin: string;
  top_results: ScoredDestination[];
  total_candidates_evaluated: number;
  total_candidates_filtered: number;
  data_source: string;
  warnings: string[];
  llm_explanation: string;
  execution_stats: SearchExecutionStats | null;
}

export interface NaturalLanguageSearchResponse {
  parsed_request: SearchRequest | null;
  search_response: SearchResponse | null;
  llm_explanation: string;
  parse_error: string;
}

export interface TravelAdviceResponse {
  destination_id: number;
  city: string;
  state: string;
  advice: string;
}

export interface Destination {
  id: number;
  city: string;
  state: string;
  iata_code: string;
  latitude: number;
  longitude: number;
  cost_level: number;
  public_transport_score: number;
  walkability_score: number;
  tags: string[];
}

export interface DestinationDetail extends Destination {
  country: string;
  timezone: string;
  monthly_climate: {
    month: number;
    temp_max_avg_c: number;
    temp_min_avg_c: number;
    precip_days: number;
    precip_mm: number;
    sunshine_hours: number;
    uv_index_avg: number;
  }[];
}

export interface SearchHistoryItem {
  id: string;
  origin: string;
  preferred_departure_date: string;
  budget: number;
  preferences: string[];
  status: string;
  created_at: string | null;
}

export interface SearchHistoryDetail {
  id: string;
  origin: string;
  preferred_departure_date: string;
  date_flexibility_days: number;
  trip_length_min: number;
  trip_length_max: number;
  budget: number;
  currency: string;
  preferences: string[];
  constraints: Record<string, unknown>;
  status: string;
  created_at: string | null;
  completed_at: string | null;
  results: {
    destination_id: number;
    departure_date: string;
    return_date: string;
    flight_price: number;
    hotel_price: number;
    estimated_total: number;
    total_score: number;
    recommendation_reason: string;
    scores: ScoreBreakdown;
  }[];
}

export interface HealthResponse {
  status: string;
  version: string;
  providers: {
    flight: string;
    hotel: string;
    weather: string;
  };
  llm: {
    enabled: boolean;
    model: string | null;
  };
  destinations_count: number;
  cache: {
    flights: { total: number; valid: number };
    hotels: { total: number; valid: number };
  };
}

export const PREFERENCE_OPTIONS = [
  { value: "beach", label: "海滩" },
  { value: "nature", label: "自然" },
  { value: "food", label: "美食" },
  { value: "city", label: "城市" },
  { value: "museum", label: "博物馆" },
  { value: "nightlife", label: "夜生活" },
  { value: "relaxation", label: "休闲" },
  { value: "hiking", label: "徒步" },
  { value: "public_transport", label: "公共交通" },
  { value: "family", label: "亲子" },
  { value: "budget", label: "经济" },
  { value: "music", label: "音乐" },
  { value: "history", label: "历史" },
  { value: "coffee", label: "咖啡" },
  { value: "outdoor", label: "户外" },
  { value: "skiing", label: "滑雪" },
  { value: "architecture", label: "建筑" },
  { value: "art", label: "艺术" },
  { value: "shopping", label: "购物" },
  { value: "entertainment", label: "娱乐" },
];
