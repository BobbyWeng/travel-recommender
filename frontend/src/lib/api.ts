import type {
  SearchRequest,
  SearchResponse,
  Destination,
  DestinationDetail,
  HealthResponse,
  SearchHistoryItem,
  SearchHistoryDetail,
  NaturalLanguageSearchRequest,
  NaturalLanguageSearchResponse,
  TravelAdviceRequest,
  TravelAdviceResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function searchDestinations(
  request: SearchRequest
): Promise<SearchResponse> {
  return fetchAPI<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function searchWithExplanation(
  request: SearchRequest
): Promise<SearchResponse> {
  return fetchAPI<SearchResponse>("/search/explain", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function explainSearchResults(
  searchId: string,
  originalQuery: string = ""
): Promise<{ explanation: string }> {
  return fetchAPI<{ explanation: string }>("/explain", {
    method: "POST",
    body: JSON.stringify({ search_id: searchId, original_query: originalQuery }),
  });
}

export async function naturalLanguageSearch(
  query: string
): Promise<NaturalLanguageSearchResponse> {
  return fetchAPI<NaturalLanguageSearchResponse>("/search/natural", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

export async function getTravelAdvice(
  destinationId: number,
  preferences: string[] = []
): Promise<TravelAdviceResponse> {
  return fetchAPI<TravelAdviceResponse>(
    `/destinations/${destinationId}/advice`,
    {
      method: "POST",
      body: JSON.stringify({ destination_id: destinationId, preferences }),
    }
  );
}

export async function getSearchResult(searchId: string): Promise<SearchResponse> {
  return fetchAPI<SearchResponse>(`/search/${searchId}`);
}

export async function listSearches(
  limit: number = 20,
  offset: number = 0
): Promise<SearchHistoryItem[]> {
  return fetchAPI<SearchHistoryItem[]>(
    `/searches?limit=${limit}&offset=${offset}`
  );
}

export async function getSearchDetail(
  searchId: string
): Promise<SearchHistoryDetail> {
  return fetchAPI<SearchHistoryDetail>(`/searches/${searchId}`);
}

export async function listDestinations(
  params?: { tags?: string; min_transit?: number }
): Promise<Destination[]> {
  const sp = new URLSearchParams();
  if (params?.tags) sp.set("tags", params.tags);
  if (params?.min_transit !== undefined)
    sp.set("min_transit", String(params.min_transit));
  const qs = sp.toString();
  return fetchAPI<Destination[]>(`/destinations${qs ? `?${qs}` : ""}`);
}

export async function getDestination(
  destId: number
): Promise<DestinationDetail> {
  return fetchAPI<DestinationDetail>(`/destinations/${destId}`);
}

export async function getHealth(): Promise<HealthResponse> {
  return fetchAPI<HealthResponse>("/health");
}

export async function cleanupCache(): Promise<{ cleaned: { flights: number; hotels: number } }> {
  return fetchAPI("/cache/cleanup", { method: "POST" });
}
