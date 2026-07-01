import type {
  SearchRequest,
  SearchResponse,
  Destination,
  DestinationDetail,
  HealthResponse,
  SearchHistoryItem,
  SearchHistoryDetail,
  NaturalLanguageSearchResponse,
  TravelAdviceResponse,
  APIError,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...options?.headers },
      ...options,
    });
  } catch {
    const apiError: APIError = {
      message: "网络连接失败，请检查网络后重试",
      code: "NETWORK_ERROR",
    };
    throw apiError;
  }
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    let message: string;
    if (res.status === 404) {
      message = "请求的资源不存在";
    } else if (res.status >= 400 && res.status < 500) {
      message = "请求参数有误，请检查输入";
    } else {
      message = "服务器暂时不可用，请稍后重试";
    }
    const apiError: APIError = {
      status: res.status,
      code: `${res.status}`,
      message,
      detail: errorBody.detail || res.statusText,
    };
    throw apiError;
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
