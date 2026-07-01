"use client";

import type { ScoredDestination } from "@/lib/types";
import { formatPrice, formatDate } from "@/lib/utils";

interface ComparePanelProps {
  destinations: ScoredDestination[];
  onRemove: (id: number) => void;
}

export default function ComparePanel({
  destinations,
  onRemove,
}: ComparePanelProps) {
  if (destinations.length < 2) return null;

  const rows: { label: string; key: string; render: (d: ScoredDestination) => React.ReactNode }[] = [
    { label: "日期", key: "date", render: (d) => `${formatDate(d.departure_date)} ~ ${formatDate(d.return_date)} (${d.nights}晚)` },
    { label: "总分", key: "score", render: (d) => <span className="font-bold text-lg">{d.total_score.toFixed(1)}</span> },
    { label: "机票", key: "flight", render: (d) => formatPrice(d.flight_price) },
    { label: "酒店", key: "hotel", render: (d) => formatPrice(d.hotel_price) },
    { label: "总计", key: "total", render: (d) => <span className="font-bold text-blue-700">{formatPrice(d.estimated_total)}</span> },
    { label: "天气", key: "weather", render: (d) => d.weather_summary },
    { label: "机票评分", key: "s_flight", render: (d) => d.scores.flight.toFixed(0) },
    { label: "酒店评分", key: "s_hotel", render: (d) => d.scores.hotel.toFixed(0) },
    { label: "天气评分", key: "s_weather", render: (d) => d.scores.weather.toFixed(0) },
    { label: "偏好匹配", key: "s_pref", render: (d) => d.scores.preference_match.toFixed(0) },
    { label: "交通评分", key: "s_transport", render: (d) => d.scores.transport.toFixed(0) },
    { label: "活动评分", key: "s_activity", render: (d) => d.scores.activities.toFixed(0) },
  ];

  const getBest = (key: string): number => {
    const vals = destinations.map((d) => {
      const scoreKey = key.startsWith("s_") ? key.slice(2) : key;
      if (key === "score" || key.startsWith("s_")) return d.scores[scoreKey as keyof typeof d.scores] as number;
      if (key === "total" || key === "flight" || key === "hotel") return -d[key as keyof typeof d] as number;
      return d.total_score;
    });
    return vals.indexOf(Math.max(...vals));
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">目的地对比</h3>
        <span className="text-sm text-gray-400">
          已选 {destinations.length} 个（最多 3 个）
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left py-2 pr-4 text-gray-500 font-medium w-24"></th>
              {destinations.map((d) => (
                <th key={d.destination_id} className="text-center py-2 px-3">
                  <div className="font-semibold text-gray-900">
                    {d.city}, {d.state}
                  </div>
                  <button
                    onClick={() => onRemove(d.destination_id)}
                    className="text-xs text-red-400 hover:text-red-600 mt-1"
                  >
                    移除
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const bestIdx = getBest(row.key);
              return (
                <tr key={row.key} className="border-b border-gray-50">
                  <td className="py-2 pr-4 text-gray-500">{row.label}</td>
                  {destinations.map((d, i) => (
                    <td
                      key={d.destination_id}
                      className={`text-center py-2 px-3 ${
                        i === bestIdx ? "bg-emerald-50 font-medium" : ""
                      }`}
                    >
                      {row.render(d)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
