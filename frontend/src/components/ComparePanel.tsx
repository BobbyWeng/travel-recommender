"use client";

import type { ScoredDestination } from "@/lib/types";
import { formatPrice, formatDate, dataKindLabel } from "@/lib/utils";

type CompareMetric = {
  label: string;
  getValue: (item: ScoredDestination) => number | string | null;
  better: "higher" | "lower" | "none";
  format?: (value: number | string | null) => string;
  key: string;
};

interface ComparePanelProps {
  destinations: ScoredDestination[];
  onRemove: (id: number) => void;
}

const metrics: CompareMetric[] = [
  {
    label: "日期",
    key: "date",
    better: "none",
    getValue: (d) => `${formatDate(d.departure_date)} ~ ${formatDate(d.return_date)} (${d.nights}晚)`,
  },
  {
    label: "总分",
    key: "score",
    better: "higher",
    getValue: (d) => d.total_score,
  },
  {
    label: "机票",
    key: "flight_price",
    better: "lower",
    getValue: (d) => d.flight_price,
  },
  {
    label: "酒店",
    key: "hotel_price",
    better: "lower",
    getValue: (d) => d.hotel_price,
  },
  {
    label: "总计",
    key: "estimated_total",
    better: "lower",
    getValue: (d) => d.estimated_total,
  },
  {
    label: "天气",
    key: "weather_summary",
    better: "none",
    getValue: (d) => d.weather_summary,
  },
  {
    label: "机票评分",
    key: "scores.flight",
    better: "higher",
    getValue: (d) => d.scores.flight,
  },
  {
    label: "酒店评分",
    key: "scores.hotel",
    better: "higher",
    getValue: (d) => d.scores.hotel,
  },
  {
    label: "天气评分",
    key: "scores.weather",
    better: "higher",
    getValue: (d) => d.scores.weather,
  },
  {
    label: "偏好匹配",
    key: "scores.preference_match",
    better: "higher",
    getValue: (d) => d.scores.preference_match,
  },
  {
    label: "交通评分",
    key: "scores.transport",
    better: "higher",
    getValue: (d) => d.scores.transport,
  },
  {
    label: "活动评分",
    key: "scores.activities",
    better: "higher",
    getValue: (d) => d.scores.activities,
  },
  {
    label: "航班数据类型",
    key: "flight_data_kind",
    better: "none",
    getValue: (d) => dataKindLabel(d.flight_data_kind) || "-",
  },
  {
    label: "酒店数据类型",
    key: "hotel_data_kind",
    better: "none",
    getValue: (d) => dataKindLabel(d.hotel_data_kind) || "-",
  },
  {
    label: "天气数据类型",
    key: "weather_data_kind",
    better: "none",
    getValue: (d) => dataKindLabel(d.weather_data_kind) || "-",
  },
];

function renderMetricValue(metric: CompareMetric, d: ScoredDestination): React.ReactNode {
  const val = metric.getValue(d);
  if (metric.key === "score" && typeof val === "number") {
    return <span className="font-bold text-lg">{val.toFixed(1)}</span>;
  }
  if ((metric.key === "flight_price" || metric.key === "hotel_price") && typeof val === "number") {
    return val === 0 ? <span className="text-gray-400 text-xs">暂无数据</span> : formatPrice(val);
  }
  if (metric.key === "estimated_total" && typeof val === "number") {
    return <span className="font-bold text-blue-700">{formatPrice(val)}</span>;
  }
  if (metric.key.startsWith("scores.") && typeof val === "number") {
    return val.toFixed(0);
  }
  return String(val ?? "");
}

export default function ComparePanel({
  destinations,
  onRemove,
}: ComparePanelProps) {
  if (destinations.length < 2) return null;

  const getBest = (metric: CompareMetric): number => {
    if (metric.better === "none") return -1;
    const numericVals = destinations.map((d) => {
      const v = metric.getValue(d);
      return typeof v === "number" ? v : null;
    });
    if (numericVals.every((v) => v === null)) return -1;
    if (metric.better === "lower") {
      let minVal = Infinity;
      let minIdx = -1;
      numericVals.forEach((v, i) => {
        if (v !== null && v < minVal) {
          minVal = v;
          minIdx = i;
        }
      });
      return minIdx;
    }
    let maxVal = -Infinity;
    let maxIdx = -1;
    numericVals.forEach((v, i) => {
      if (v !== null && v > maxVal) {
        maxVal = v;
        maxIdx = i;
      }
    });
    return maxIdx;
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
            {metrics.map((metric) => {
              const bestIdx = getBest(metric);
              return (
                <tr key={metric.key} className="border-b border-gray-50">
                  <td className="py-2 pr-4 text-gray-500">{metric.label}</td>
                  {destinations.map((d, i) => (
                    <td
                      key={d.destination_id}
                      className={`text-center py-2 px-3 ${
                        i === bestIdx ? "bg-emerald-50 font-medium" : ""
                      }`}
                    >
                      {renderMetricValue(metric, d)}
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
