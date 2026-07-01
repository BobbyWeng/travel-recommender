"use client";

import { useState } from "react";
import { PREFERENCE_OPTIONS } from "@/lib/types";

interface SearchFormProps {
  onSearch: (data: {
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
    domesticOnly: boolean;
  }) => void;
  isLoading?: boolean;
}

export default function SearchForm({ onSearch, isLoading }: SearchFormProps) {
  const [origin, setOrigin] = useState("ATL");
  const [date, setDate] = useState("");
  const [flex, setFlex] = useState(5);
  const [minNights, setMinNights] = useState(4);
  const [maxNights, setMaxNights] = useState(6);
  const [budget, setBudget] = useState(1500);
  const [preferences, setPreferences] = useState<string[]>(["nature", "food"]);
  const [maxFlightHours, setMaxFlightHours] = useState(8);
  const [maxStops, setMaxStops] = useState(1);
  const [avoidHotWeather, setAvoidHotWeather] = useState(true);
  const [avoidColdWeather, setAvoidColdWeather] = useState(false);
  const [noCarRental, setNoCarRental] = useState(true);
  const [domesticOnly, setDomesticOnly] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const togglePreference = (val: string) => {
    setPreferences((prev) =>
      prev.includes(val) ? prev.filter((p) => p !== val) : [...prev, val]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch({
      origin: origin.toUpperCase(),
      date,
      flex,
      minNights,
      maxNights,
      budget,
      preferences,
      maxFlightHours: maxFlightHours || undefined,
      maxStops: maxStops !== undefined ? maxStops : undefined,
      avoidHotWeather,
      avoidColdWeather,
      noCarRental,
      domesticOnly,
    });
  };

  const today = new Date().toISOString().split("T")[0];

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            出发机场
          </label>
          <input
            type="text"
            value={origin}
            onChange={(e) => setOrigin(e.target.value.toUpperCase())}
            maxLength={3}
            placeholder="ATL"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-center text-lg font-mono"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            出发日期
          </label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            min={today}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            预算 (USD)
          </label>
          <input
            type="number"
            value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
            min={100}
            step={100}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            旅行天数
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={minNights}
              onChange={(e) => setMinNights(Number(e.target.value))}
              min={1}
              max={30}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <span className="text-gray-500">至</span>
            <input
              type="number"
              value={maxNights}
              onChange={(e) => setMaxNights(Number(e.target.value))}
              min={minNights}
              max={30}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          旅行偏好
        </label>
        <div className="flex flex-wrap gap-2">
          {PREFERENCE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => togglePreference(opt.value)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                preferences.includes(opt.value)
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
        >
          <svg
            className={`w-4 h-4 transition-transform ${showAdvanced ? "rotate-90" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
          高级选项
        </button>
      </div>

      {showAdvanced && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              日期浮动 (天)
            </label>
            <input
              type="number"
              value={flex}
              onChange={(e) => setFlex(Number(e.target.value))}
              min={0}
              max={14}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              最大飞行时间 (小时)
            </label>
            <input
              type="number"
              value={maxFlightHours}
              onChange={(e) => setMaxFlightHours(Number(e.target.value))}
              min={1}
              max={30}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              最大中转次数
            </label>
            <input
              type="number"
              value={maxStops}
              onChange={(e) => setMaxStops(Number(e.target.value))}
              min={0}
              max={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={avoidHotWeather}
                onChange={(e) => setAvoidHotWeather(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <span className="text-sm text-gray-700">避免炎热</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={avoidColdWeather}
                onChange={(e) => setAvoidColdWeather(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <span className="text-sm text-gray-700">避免寒冷</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={noCarRental}
                onChange={(e) => setNoCarRental(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <span className="text-sm text-gray-700">不租车</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={domesticOnly}
                onChange={(e) => setDomesticOnly(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <span className="text-sm text-gray-700">仅美国国内</span>
            </label>
          </div>
          <div className="text-xs text-gray-400 mt-1">当前数据集以美国目的地为主</div>
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <svg
              className="animate-spin h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            搜索中...
          </>
        ) : (
          "搜索推荐目的地"
        )}
      </button>
    </form>
  );
}
