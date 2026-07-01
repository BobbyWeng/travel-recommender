"use client";

import { useState, useEffect } from "react";
import { listSearches, getSearchDetail } from "@/lib/api";
import type { SearchHistoryItem, SearchHistoryDetail } from "@/lib/types";
import { formatDate, formatPrice, scoreColor } from "@/lib/utils";

export default function SearchHistory() {
  const [searches, setSearches] = useState<SearchHistoryItem[]>([]);
  const [selected, setSelected] = useState<SearchHistoryDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSearches();
  }, []);

  async function loadSearches() {
    try {
      const data = await listSearches(50, 0);
      setSearches(data);
    } catch {
    } finally {
      setLoading(false);
    }
  }

  async function handleSelect(id: string) {
    try {
      const detail = await getSearchDetail(id);
      setSelected(detail);
    } catch {}
  }

  if (loading) {
    return (
      <div className="text-center py-8 text-gray-400">加载中...</div>
    );
  }

  if (searches.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        暂无搜索历史
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-1 space-y-2">
        <h3 className="text-sm font-semibold text-gray-500 mb-3">搜索历史</h3>
        {searches.map((s) => (
          <button
            key={s.id}
            onClick={() => handleSelect(s.id)}
            className={`w-full text-left p-3 rounded-lg border transition-all text-sm ${
              selected?.id === s.id
                ? "border-blue-400 bg-blue-50"
                : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
            }`}
          >
            <div className="flex justify-between items-center">
              <span className="font-medium text-gray-900">{s.origin}</span>
              <span className="text-xs text-gray-400">
                {s.created_at ? new Date(s.created_at).toLocaleDateString("zh-CN") : ""}
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {formatDate(s.preferred_departure_date)} · {formatPrice(s.budget)} 预算
            </div>
            {s.preferences.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1.5">
                {s.preferences.slice(0, 3).map((p) => (
                  <span
                    key={p}
                    className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded"
                  >
                    {p}
                  </span>
                ))}
                {s.preferences.length > 3 && (
                  <span className="text-xs text-gray-400">
                    +{s.preferences.length - 3}
                  </span>
                )}
              </div>
            )}
          </button>
        ))}
      </div>

      <div className="lg:col-span-2">
        {selected ? (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">搜索结果</h3>
              <span className="text-xs text-gray-400">
                {selected.completed_at
                  ? new Date(selected.completed_at).toLocaleString("zh-CN")
                  : ""}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
              <div className="bg-gray-50 rounded-lg p-3">
                <span className="text-gray-500">出发地</span>
                <span className="ml-2 font-medium">{selected.origin}</span>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <span className="text-gray-500">预算</span>
                <span className="ml-2 font-medium">{formatPrice(selected.budget)}</span>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <span className="text-gray-500">日期</span>
                <span className="ml-2 font-medium">
                  {formatDate(selected.preferred_departure_date)} ({selected.trip_length_min}-{selected.trip_length_max}晚)
                </span>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <span className="text-gray-500">结果数</span>
                <span className="ml-2 font-medium">{selected.results.length} 个推荐</span>
              </div>
            </div>

            <div className="space-y-3">
              {selected.results.map((r, i) => (
                <div
                  key={i}
                  className="border border-gray-200 rounded-lg p-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span
                        className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                          i < 2
                            ? "bg-emerald-600 text-white"
                            : "bg-gray-200 text-gray-600"
                        }`}
                      >
                        {i + 1}
                      </span>
                      <div>
                        <span className="font-medium text-gray-900">
                          目的地 #{r.destination_id}
                        </span>
                        <span className="text-sm text-gray-500 ml-2">
                          {formatDate(r.departure_date)} ~ {formatDate(r.return_date)}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`text-xl font-bold ${scoreColor(r.total_score)}`}>
                        {r.total_score.toFixed(1)}
                      </span>
                      <div className="text-xs text-gray-400">
                        {formatPrice(r.estimated_total)}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-6 gap-2 mt-3">
                    {[
                      { label: "机票", value: r.scores.flight },
                      { label: "酒店", value: r.scores.hotel },
                      { label: "天气", value: r.scores.weather },
                      { label: "偏好", value: r.scores.preference_match },
                      { label: "交通", value: r.scores.transport },
                      { label: "活动", value: r.scores.activities },
                    ].map((s) => (
                      <div key={s.label} className="text-center">
                        <div className="text-xs text-gray-400">{s.label}</div>
                        <div
                          className={`text-sm font-medium ${
                            s.value >= 80
                              ? "text-emerald-600"
                              : s.value >= 60
                              ? "text-amber-600"
                              : "text-red-600"
                          }`}
                        >
                          {s.value.toFixed(0)}
                        </div>
                      </div>
                    ))}
                  </div>

                  {r.recommendation_reason && (
                    <div className="mt-2 text-xs text-gray-400">
                      {r.recommendation_reason}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-center py-16 text-gray-400">
            点击左侧搜索记录查看详情
          </div>
        )}
      </div>
    </div>
  );
}
