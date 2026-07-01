"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getDestination, getTravelAdvice } from "@/lib/api";
import type { DestinationDetail, TravelAdviceResponse, APIError } from "@/lib/types";

const MONTH_NAMES = [
  "", "1月", "2月", "3月", "4月", "5月", "6月",
  "7月", "8月", "9月", "10月", "11月", "12月",
];

export default function DestinationPage() {
  const params = useParams();
  const router = useRouter();
  const [dest, setDest] = useState<DestinationDetail | null>(null);
  const [advice, setAdvice] = useState<TravelAdviceResponse | null>(null);
  const [adviceLoading, setAdviceLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (params.id) {
      loadDestination(Number(params.id));
    }
  }, [params.id]);

  async function loadDestination(id: number) {
    try {
      const data = await getDestination(id);
      setDest(data);
    } catch (err) {
      console.error("Failed to load destination:", (err as APIError)?.message || (err instanceof Error ? err.message : err));
      setError((err as APIError)?.message || "加载目的地失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleGetAdvice() {
    if (!dest) return;
    setAdviceLoading(true);
    try {
      const result = await getTravelAdvice(dest.id);
      setAdvice(result);
    } catch (err) {
      console.error("Failed to get travel advice:", (err as APIError)?.message || (err instanceof Error ? err.message : err));
      setError((err as APIError)?.message || "获取旅行建议失败");
    } finally {
      setAdviceLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 text-center text-gray-400">
        加载中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 mb-4">{error}</div>
        <button
          onClick={() => router.push("/")}
          className="text-blue-500 hover:underline"
        >
          返回首页
        </button>
      </div>
    );
  }

  if (!dest) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 text-center">
        <p className="text-gray-500 mb-4">目的地未找到</p>
        <button
          onClick={() => router.push("/")}
          className="text-blue-500 hover:underline"
        >
          返回首页
        </button>
      </div>
    );
  }

  const climate = dest.monthly_climate;
  const maxTemp = Math.max(...climate.map((c) => c.temp_max_avg_c));
  const minTemp = Math.min(...climate.map((c) => c.temp_min_avg_c));
  const tempRange = maxTemp - minTemp;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <button
        onClick={() => router.push("/")}
        className="text-sm text-gray-400 hover:text-gray-600 flex items-center gap-1"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        返回搜索
      </button>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {dest.city}, {dest.state}
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              {dest.country} · {dest.iata_code} · {dest.timezone}
            </p>
          </div>
          <div className="flex gap-2">
            <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full">
              消费等级 {dest.cost_level}/5
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mt-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-500">公共交通</div>
            <div className="flex items-center gap-2 mt-1">
              <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    dest.public_transport_score >= 7
                      ? "bg-emerald-500"
                      : dest.public_transport_score >= 5
                      ? "bg-amber-500"
                      : "bg-red-500"
                  }`}
                  style={{ width: `${dest.public_transport_score * 10}%` }}
                />
              </div>
              <span className="text-sm font-medium">{dest.public_transport_score}/10</span>
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-500">步行友好度</div>
            <div className="flex items-center gap-2 mt-1">
              <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    dest.walkability_score >= 7
                      ? "bg-emerald-500"
                      : dest.walkability_score >= 5
                      ? "bg-amber-500"
                      : "bg-red-500"
                  }`}
                  style={{ width: `${dest.walkability_score * 10}%` }}
                />
              </div>
              <span className="text-sm font-medium">{dest.walkability_score}/10</span>
            </div>
          </div>
        </div>

        <div className="mt-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">特色标签</h3>
          <div className="flex flex-wrap gap-2">
            {dest.tags.map((tag) => (
              <span
                key={tag}
                className="text-xs px-3 py-1 bg-blue-50 text-blue-600 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">月度气候</h2>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left py-2 px-2 text-gray-500 font-medium">月份</th>
                <th className="text-center py-2 px-2 text-gray-500 font-medium">温度范围</th>
                <th className="text-center py-2 px-2 text-gray-500 font-medium">降水天数</th>
                <th className="text-center py-2 px-2 text-gray-500 font-medium">降水量</th>
                <th className="text-center py-2 px-2 text-gray-500 font-medium">日照时数</th>
                <th className="text-center py-2 px-2 text-gray-500 font-medium">UV指数</th>
              </tr>
            </thead>
            <tbody>
              {climate.map((c) => {
                const barLeft = tempRange > 0 ? ((c.temp_min_avg_c - minTemp) / tempRange) * 100 : 0;
                const barWidth = tempRange > 0 ? ((c.temp_max_avg_c - c.temp_min_avg_c) / tempRange) * 100 : 0;

                return (
                  <tr key={c.month} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 px-2 font-medium text-gray-900">
                      {MONTH_NAMES[c.month]}
                    </td>
                    <td className="py-2 px-2">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden relative">
                          <div
                            className="absolute h-full bg-gradient-to-r from-blue-300 to-orange-400 rounded-full"
                            style={{
                              left: `${barLeft}%`,
                              width: `${Math.max(barWidth, 3)}%`,
                            }}
                          />
                        </div>
                        <span className="text-xs text-gray-500 w-24 text-right whitespace-nowrap">
                          {c.temp_min_avg_c}°~{c.temp_max_avg_c}°C
                        </span>
                      </div>
                    </td>
                    <td className="py-2 px-2 text-center text-gray-600">
                      {c.precip_days}
                    </td>
                    <td className="py-2 px-2 text-center text-gray-600">
                      {c.precip_mm}mm
                    </td>
                    <td className="py-2 px-2 text-center text-gray-600">
                      {c.sunshine_hours}h
                    </td>
                    <td className="py-2 px-2 text-center text-gray-600">
                      {c.uv_index_avg}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-6">
          <h3 className="text-sm font-medium text-gray-500 mb-3">温度趋势</h3>
          <div className="flex items-end gap-1 h-32">
            {climate.map((c) => {
              const heightPct = tempRange > 0
                ? ((c.temp_max_avg_c - minTemp) / tempRange) * 100
                : 50;
              const minPct = tempRange > 0
                ? ((c.temp_min_avg_c - minTemp) / tempRange) * 100
                : 0;

              return (
                <div key={c.month} className="flex-1 flex flex-col items-center">
                  <div className="w-full relative" style={{ height: "100px" }}>
                    <div
                      className="absolute bottom-0 w-full bg-gradient-to-t from-blue-200 to-orange-300 rounded-t"
                      style={{
                        height: `${heightPct}%`,
                        minHeight: "4px",
                      }}
                    />
                    <div
                      className="absolute bottom-0 w-full bg-blue-400 rounded-t"
                      style={{
                        height: `${minPct}%`,
                        minHeight: "2px",
                      }}
                    />
                  </div>
                  <span className="text-xs text-gray-400 mt-1">
                    {MONTH_NAMES[c.month]}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl shadow-sm border border-purple-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            <h2 className="text-lg font-semibold text-purple-900">AI 旅行建议</h2>
          </div>
          {!advice && (
            <button
              onClick={handleGetAdvice}
              disabled={adviceLoading}
              className="text-sm px-4 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition"
            >
              {adviceLoading ? "生成中..." : "获取建议"}
            </button>
          )}
        </div>

        {adviceLoading && !advice && (
          <div className="flex items-center gap-2 text-sm text-purple-600">
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            AI 正在为 {dest.city} 生成旅行建议...
          </div>
        )}

        {advice && (
          <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {advice.advice}
          </div>
        )}

        {!advice && !adviceLoading && (
          <p className="text-sm text-purple-400">
            点击"获取建议"，让 AI 为你生成 {dest.city} 的旅行建议
          </p>
        )}
      </div>
    </div>
  );
}
