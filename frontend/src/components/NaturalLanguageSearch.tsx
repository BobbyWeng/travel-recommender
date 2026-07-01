"use client";

import { useState } from "react";
import { naturalLanguageSearch } from "@/lib/api";
import type { NaturalLanguageSearchResponse, SearchRequest } from "@/lib/types";

interface NaturalLanguageSearchProps {
  onSearchResult: (response: NaturalLanguageSearchResponse) => void;
  onParsedSearch?: (request: SearchRequest) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

const EXAMPLE_QUERIES = [
  "9月份从亚特兰大出发，5天左右，预算1500美元，想去有自然风光和美食的地方",
  "暑假带家人去海边，预算2000，不租车",
  "秋天去一个有历史和咖啡文化的城市，预算1000",
  "冬天想去暖和的地方徒步，预算1800",
];

export default function NaturalLanguageSearch({
  onSearchResult,
  isLoading,
  setIsLoading,
}: NaturalLanguageSearchProps) {
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setIsLoading(true);
    setError(null);

    try {
      const result = await naturalLanguageSearch(query.trim());
      onSearchResult(result);
      if (result.parse_error) {
        setError(result.parse_error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "搜索失败");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="flex-1 relative">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="用自然语言描述你的旅行需求，例如：9月从亚特兰大出发，5天左右，预算1500，想去有自然风光和美食的地方"
            className="w-full border border-gray-300 rounded-lg px-4 py-3 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent resize-none"
            rows={2}
            disabled={isLoading}
          />
          <button
            onClick={handleSearch}
            disabled={isLoading || !query.trim()}
            className="absolute right-2 bottom-2 p-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {isLoading ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          {error}
        </div>
      )}

      <div className="flex flex-wrap gap-1.5">
        <span className="text-xs text-gray-400 py-0.5">试试：</span>
        {EXAMPLE_QUERIES.map((q, i) => (
          <button
            key={i}
            onClick={() => setQuery(q)}
            className="text-xs px-2 py-0.5 bg-purple-50 text-purple-600 rounded-full hover:bg-purple-100 transition truncate max-w-[200px]"
          >
            {q.slice(0, 20)}...
          </button>
        ))}
      </div>
    </div>
  );
}
