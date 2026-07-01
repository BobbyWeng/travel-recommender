"use client";

import type { ScoredDestination } from "@/lib/types";
import { formatPrice, formatDate, scoreColor } from "@/lib/utils";

interface ResultCardProps {
  result: ScoredDestination;
  rank: number;
  onSelect?: (result: ScoredDestination) => void;
  selected?: boolean;
}

function DataSourceBadge({ source }: { source: string }) {
  const sources = source.split("+");
  const isReal = sources.some((s) => s === "amadeus" || s === "open-meteo");
  const isMock = sources.some((s) => s === "mock");
  const isCached = sources.some((s) => s === "cached");

  if (isCached) {
    return (
      <span className="inline-flex items-center text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full">
        缓存数据
      </span>
    );
  }

  if (isReal && !isMock) {
    return (
      <span className="inline-flex items-center text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full">
        <span className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-1" />
        实时数据
      </span>
    );
  }

  if (isReal && isMock) {
    return (
      <span className="inline-flex items-center text-xs px-2 py-0.5 bg-amber-50 text-amber-600 rounded-full">
        <span className="w-1.5 h-1.5 bg-amber-500 rounded-full mr-1" />
        部分 Mock
      </span>
    );
  }

  return (
    <span className="inline-flex items-center text-xs px-2 py-0.5 bg-gray-50 text-gray-400 rounded-full">
      Mock 数据
    </span>
  );
}

export default function ResultCard({
  result,
  rank,
  onSelect,
  selected,
}: ResultCardProps) {
  const scoreBars = [
    { label: "机票", value: result.scores.flight },
    { label: "酒店", value: result.scores.hotel },
    { label: "天气", value: result.scores.weather },
    { label: "偏好", value: result.scores.preference_match },
    { label: "交通", value: result.scores.transport },
    { label: "活动", value: result.scores.activities },
  ];

  return (
    <div
      onClick={() => onSelect?.(result)}
      className={`border rounded-xl p-5 cursor-pointer transition-all hover:shadow-lg ${
        selected
          ? "border-blue-500 ring-2 ring-blue-200 shadow-md"
          : rank <= 2
          ? "border-emerald-200 bg-emerald-50/30"
          : "border-gray-200 bg-white"
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-sm font-bold ${
                rank <= 2
                  ? "bg-emerald-600 text-white"
                  : "bg-gray-200 text-gray-600"
              }`}
            >
              {rank}
            </span>
            <h3 className="text-lg font-semibold text-gray-900">
              {result.city},{" "}
              <span className="text-gray-500 font-normal">{result.state}</span>
            </h3>
            <DataSourceBadge source={result.data_source} />
          </div>
          <p className="text-sm text-gray-500 mt-1 ml-9">
            {formatDate(result.departure_date)} ~ {formatDate(result.return_date)}{" "}
            ({result.nights}晚)
          </p>
        </div>
        <div className="text-right">
          <div className={`text-2xl font-bold ${scoreColor(result.total_score)}`}>
            {result.total_score.toFixed(1)}
          </div>
          <div className="text-xs text-gray-400">总分</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4 text-sm">
        <div className="bg-gray-50 rounded-lg p-2 text-center">
          <div className="text-gray-500 text-xs">机票</div>
          <div className="font-semibold text-gray-900">
            {formatPrice(result.flight_price)}
          </div>
        </div>
        <div className="bg-gray-50 rounded-lg p-2 text-center">
          <div className="text-gray-500 text-xs">酒店</div>
          <div className="font-semibold text-gray-900">
            {formatPrice(result.hotel_price)}
          </div>
        </div>
        <div className="bg-blue-50 rounded-lg p-2 text-center">
          <div className="text-blue-600 text-xs">总计</div>
          <div className="font-bold text-blue-700">
            {formatPrice(result.estimated_total)}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-3 text-sm text-gray-600">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
        </svg>
        {result.weather_summary}
      </div>

      <div className="grid grid-cols-6 gap-1 mb-3">
        {scoreBars.map((bar) => (
          <div key={bar.label} className="text-center">
            <div className="text-xs text-gray-400 mb-1">{bar.label}</div>
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  bar.value >= 80
                    ? "bg-emerald-500"
                    : bar.value >= 60
                    ? "bg-amber-500"
                    : "bg-red-500"
                }`}
                style={{ width: `${bar.value}%` }}
              />
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              {bar.value.toFixed(0)}
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-1">
        {result.pros.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {result.pros.map((pro, i) => (
              <span
                key={i}
                className="inline-block text-xs px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-full"
              >
                {pro}
              </span>
            ))}
          </div>
        )}
        {result.cons.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {result.cons.map((con, i) => (
              <span
                key={i}
                className="inline-block text-xs px-2 py-0.5 bg-amber-50 text-amber-700 rounded-full"
              >
                {con}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-400">
        推荐理由: {result.recommendation_reason}
      </div>
    </div>
  );
}
