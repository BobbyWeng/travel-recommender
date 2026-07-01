"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import SearchForm from "@/components/SearchForm";
import ResultCard from "@/components/ResultCard";
import ComparePanel from "@/components/ComparePanel";
import NaturalLanguageSearch from "@/components/NaturalLanguageSearch";
import LLMExplanation from "@/components/LLMExplanation";
import { searchWithExplanation, naturalLanguageSearch, explainSearchResults } from "@/lib/api";
import type {
  SearchResponse,
  ScoredDestination,
  NaturalLanguageSearchResponse as NLSearchResponse,
} from "@/lib/types";

type SearchMode = "form" | "natural";

export default function Home() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [compareIds, setCompareIds] = useState<Set<number>>(new Set());
  const [searchMode, setSearchMode] = useState<SearchMode>("form");
  const [nlParsed, setNlParsed] = useState<NLSearchResponse | null>(null);
  const [llmExplanation, setLlmExplanation] = useState("");
  const [explanationLoading, setExplanationLoading] = useState(false);

  useEffect(() => {
    if (response && !llmExplanation && !explanationLoading) {
      loadExplanation();
    }
  }, [response]);

  async function loadExplanation() {
    if (!response) return;
    setExplanationLoading(true);
    try {
      const result = await explainSearchResults(response.request_id);
      setLlmExplanation(result.explanation);
    } catch {
    } finally {
      setExplanationLoading(false);
    }
  }

  const handleFormSearch = async (data: {
    origin: string;
    date: string;
    flex: number;
    minNights: number;
    maxNights: number;
    budget: number;
    preferences: string[];
    maxFlightHours?: number;
    maxStops?: number;
    avoidHotWeather: boolean;
    avoidColdWeather: boolean;
    noCarRental: boolean;
  }) => {
    setIsLoading(true);
    setError(null);
    setResponse(null);
    setNlParsed(null);
    setLlmExplanation("");
    setCompareIds(new Set());

    try {
      const result = await searchWithExplanation({
        origin: data.origin,
        preferred_departure_date: data.date,
        date_flexibility_days: data.flex,
        trip_length_min: data.minNights,
        trip_length_max: data.maxNights,
        budget: data.budget,
        currency: "USD",
        preferences: data.preferences,
        constraints: {
          max_flight_hours: data.maxFlightHours ?? null,
          max_stops: data.maxStops ?? null,
          avoid_hot_weather: data.avoidHotWeather,
          avoid_cold_weather: data.avoidColdWeather,
          no_car_rental: data.noCarRental,
          domestic_only: true,
        },
      });
      setResponse(result);
      if (result.llm_explanation) {
        setLlmExplanation(result.llm_explanation);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "搜索失败，请稍后重试");
    } finally {
      setIsLoading(false);
    }
  };

  const handleNLSearch = async (nlResult: NLSearchResponse) => {
    setNlParsed(nlResult);
    if (nlResult.search_response) {
      setResponse(nlResult.search_response);
    }
    if (nlResult.parse_error && !nlResult.search_response) {
      setError(nlResult.parse_error);
    }
  };

  const toggleCompare = (dest: ScoredDestination) => {
    setCompareIds((prev) => {
      const next = new Set(prev);
      if (next.has(dest.destination_id)) {
        next.delete(dest.destination_id);
      } else if (next.size < 3) {
        next.add(dest.destination_id);
      }
      return next;
    });
  };

  const removeCompare = (id: number) => {
    setCompareIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const compareDestinations = response?.top_results.filter((r) =>
    compareIds.has(r.destination_id)
  ) ?? [];

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <button
            onClick={() => { setSearchMode("form"); setNlParsed(null); }}
            className={`text-sm px-3 py-1.5 rounded-lg transition ${
              searchMode === "form"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            表单搜索
          </button>
          <button
            onClick={() => setSearchMode("natural")}
            className={`text-sm px-3 py-1.5 rounded-lg transition flex items-center gap-1 ${
              searchMode === "natural"
                ? "bg-purple-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            AI 对话搜索
          </button>
        </div>

        {searchMode === "form" ? (
          <SearchForm onSearch={handleFormSearch} isLoading={isLoading} />
        ) : (
          <NaturalLanguageSearch
            onSearchResult={handleNLSearch}
            isLoading={isLoading}
            setIsLoading={setIsLoading}
          />
        )}

        {nlParsed?.parsed_request && searchMode === "natural" && (
          <div className="mt-3 p-3 bg-gray-50 rounded-lg text-xs text-gray-500">
            <span className="font-medium">AI 解析结果：</span>
            从 {nlParsed.parsed_request.origin} 出发 ·{" "}
            {nlParsed.parsed_request.preferred_departure_date} ·{" "}
            {nlParsed.parsed_request.trip_length_min}-{nlParsed.parsed_request.trip_length_max}晚 ·{" "}
            预算 ${nlParsed.parsed_request.budget} ·{" "}
            偏好: {nlParsed.parsed_request.preferences.join(", ") || "无"}
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
          {error}
        </div>
      )}

      {llmExplanation && <LLMExplanation explanation={llmExplanation} />}

      {explanationLoading && !llmExplanation && response && (
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-xl p-5">
          <div className="flex items-center gap-2 text-sm text-purple-600">
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            AI 正在分析推荐结果...
          </div>
        </div>
      )}

      {response && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              推荐结果
              <span className="text-sm font-normal text-gray-500 ml-2">
                评估 {response.total_candidates_evaluated} 个候选，过滤{" "}
                {response.total_candidates_filtered} 个
              </span>
            </h2>
            <span className="text-xs text-gray-400">
              搜索 ID: {response.request_id.slice(0, 8)}...
            </span>
          </div>

          {response.warnings.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-700">
              {response.warnings.join("; ")}
            </div>
          )}

          {response.top_results.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              没有找到符合条件的目的地，请尝试调整预算或约束条件
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {response.top_results.map((result, i) => (
                  <div key={result.destination_id} className="relative">
                    <ResultCard
                      result={result}
                      rank={i + 1}
                      onSelect={toggleCompare}
                      selected={compareIds.has(result.destination_id)}
                    />
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/destination/${result.destination_id}`);
                      }}
                      className="absolute top-5 right-5 text-xs text-blue-500 hover:text-blue-700 hover:underline"
                    >
                      详情
                    </button>
                  </div>
                ))}
              </div>

              {compareIds.size > 0 && (
                <div className="mt-6">
                  <ComparePanel
                    destinations={compareDestinations}
                    onRemove={removeCompare}
                  />
                </div>
              )}

              {compareIds.size === 0 && (
                <p className="text-center text-sm text-gray-400 mt-4">
                  点击任意目的地卡片可添加到对比（最多 3 个）
                </p>
              )}
            </>
          )}
        </div>
      )}

      {!response && !error && !isLoading && (
        <div className="text-center py-16">
          <svg
            className="w-16 h-16 text-gray-300 mx-auto mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <h3 className="text-lg font-medium text-gray-500 mb-1">
            输入旅行偏好，发现最佳目的地
          </h3>
          <p className="text-sm text-gray-400">
            填写出发地、日期和预算，或切换到 AI 对话搜索
          </p>
        </div>
      )}
    </div>
  );
}
