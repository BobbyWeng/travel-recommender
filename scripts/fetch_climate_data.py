"""
从 Open-Meteo Historical API 批量拉取候选目的地的月度气候数据
并生成 data/destinations.json

用法:
    python scripts/fetch_climate_data.py

输出:
    data/destinations.json
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

BASE_DESTINATIONS = [
    {"id": 1, "city": "New York", "state": "NY", "iata": "JFK", "lat": 40.71, "lon": -74.01, "cost": 5, "transit": 9, "walk": 9, "tags": ["city", "museum", "food", "nightlife", "shopping"]},
    {"id": 2, "city": "Los Angeles", "state": "CA", "iata": "LAX", "lat": 34.05, "lon": -118.24, "cost": 4, "transit": 4, "walk": 5, "tags": ["beach", "city", "food", "movie"]},
    {"id": 3, "city": "San Francisco", "state": "CA", "iata": "SFO", "lat": 37.77, "lon": -122.42, "cost": 5, "transit": 8, "walk": 8, "tags": ["city", "food", "nature", "museum"]},
    {"id": 4, "city": "Chicago", "state": "IL", "iata": "ORD", "lat": 41.88, "lon": -87.63, "cost": 3, "transit": 8, "walk": 7, "tags": ["city", "food", "museum", "architecture"]},
    {"id": 5, "city": "Miami", "state": "FL", "iata": "MIA", "lat": 25.76, "lon": -80.19, "cost": 4, "transit": 5, "walk": 5, "tags": ["beach", "nightlife", "food", "art"]},
    {"id": 6, "city": "Seattle", "state": "WA", "iata": "SEA", "lat": 47.61, "lon": -122.33, "cost": 4, "transit": 7, "walk": 7, "tags": ["nature", "food", "city", "coffee"]},
    {"id": 7, "city": "Boston", "state": "MA", "iata": "BOS", "lat": 42.36, "lon": -71.06, "cost": 4, "transit": 8, "walk": 9, "tags": ["city", "museum", "food", "history"]},
    {"id": 8, "city": "Denver", "state": "CO", "iata": "DEN", "lat": 39.74, "lon": -104.99, "cost": 3, "transit": 5, "walk": 5, "tags": ["nature", "hiking", "skiing"]},
    {"id": 9, "city": "Portland", "state": "OR", "iata": "PDX", "lat": 45.52, "lon": -122.68, "cost": 3, "transit": 7, "walk": 7, "tags": ["nature", "food", "coffee", "budget"]},
    {"id": 10, "city": "New Orleans", "state": "LA", "iata": "MSY", "lat": 29.95, "lon": -90.07, "cost": 3, "transit": 5, "walk": 6, "tags": ["food", "music", "nightlife", "history"]},
    {"id": 11, "city": "Nashville", "state": "TN", "iata": "BNA", "lat": 36.16, "lon": -86.78, "cost": 2, "transit": 4, "walk": 5, "tags": ["music", "food", "nightlife"]},
    {"id": 12, "city": "Austin", "state": "TX", "iata": "AUS", "lat": 30.27, "lon": -97.74, "cost": 2, "transit": 4, "walk": 5, "tags": ["food", "music", "outdoor"]},
    {"id": 13, "city": "San Diego", "state": "CA", "iata": "SAN", "lat": 32.72, "lon": -117.16, "cost": 3, "transit": 5, "walk": 6, "tags": ["beach", "nature", "food"]},
    {"id": 14, "city": "Washington", "state": "DC", "iata": "DCA", "lat": 38.91, "lon": -77.04, "cost": 4, "transit": 8, "walk": 8, "tags": ["museum", "history", "city", "food"]},
    {"id": 15, "city": "Salt Lake City", "state": "UT", "iata": "SLC", "lat": 40.76, "lon": -111.89, "cost": 2, "transit": 4, "walk": 4, "tags": ["nature", "hiking", "skiing"]},
    {"id": 16, "city": "Charleston", "state": "SC", "iata": "CHS", "lat": 32.78, "lon": -79.93, "cost": 3, "transit": 4, "walk": 7, "tags": ["food", "history", "beach", "relaxation"]},
    {"id": 17, "city": "Las Vegas", "state": "NV", "iata": "LAS", "lat": 36.17, "lon": -115.14, "cost": 3, "transit": 4, "walk": 4, "tags": ["nightlife", "food", "entertainment"]},
    {"id": 18, "city": "Phoenix", "state": "AZ", "iata": "PHX", "lat": 33.45, "lon": -112.07, "cost": 2, "transit": 3, "walk": 3, "tags": ["nature", "hiking", "golf"]},
    {"id": 19, "city": "Minneapolis", "state": "MN", "iata": "MSP", "lat": 44.98, "lon": -93.27, "cost": 2, "transit": 6, "walk": 7, "tags": ["city", "museum", "food", "nature"]},
    {"id": 20, "city": "Atlanta", "state": "GA", "iata": "ATL", "lat": 33.75, "lon": -84.39, "cost": 2, "transit": 5, "walk": 5, "tags": ["food", "history", "music", "city"]},
]

TIMEZONE_MAP = {
    "NY": "America/New_York", "CA": "America/Los_Angeles", "IL": "America/Chicago",
    "FL": "America/New_York", "WA": "America/Los_Angeles", "MA": "America/New_York",
    "CO": "America/Denver", "OR": "America/Los_Angeles", "LA": "America/Chicago",
    "TN": "America/Chicago", "TX": "America/Chicago", "DC": "America/New_York",
    "UT": "America/Denver", "SC": "America/New_York", "NV": "America/Los_Angeles",
    "AZ": "America/Phoenix", "MN": "America/Chicago", "GA": "America/New_York",
}

REQUEST_DELAY = 10.0
MAX_RETRIES = 5
RETRY_BACKOFF = 60.0


def _fallback_climate(month: int) -> dict:
    temp_baselines = {
        1: 2, 2: 4, 3: 8, 4: 13, 5: 18, 6: 23,
        7: 26, 8: 25, 9: 20, 10: 14, 11: 8, 12: 3,
    }
    t = temp_baselines.get(month, 15)
    precip_days_map = {
        1: 8, 2: 7, 3: 9, 4: 8, 5: 9, 6: 7,
        7: 6, 8: 6, 9: 7, 10: 7, 11: 8, 12: 8,
    }
    uv_map = {
        1: 2, 2: 3, 3: 4, 4: 6, 5: 7, 6: 9,
        7: 9, 8: 8, 9: 6, 10: 4, 11: 3, 12: 2,
    }
    return {
        "month": month,
        "temp_avg_c": t,
        "temp_max_avg_c": t + 5,
        "temp_min_avg_c": t - 5,
        "precip_days": precip_days_map.get(month, 7),
        "precip_mm": precip_days_map.get(month, 7) * 3,
        "sunshine_hours": round(max(4, 10 - precip_days_map.get(month, 7) * 0.5), 1),
        "uv_index_avg": uv_map.get(month, 5),
        "wind_speed_avg_kmh": 12.0,
    }


async def fetch_monthly_climate(client: httpx.AsyncClient, lat: float, lon: float, month: int) -> dict:
    end_days = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    start_date = f"2020-{month:02d}-01"
    end_date = f"2023-{month:02d}-{end_days[month]}"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "timezone": "auto",
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.get(
                "https://archive-api.open-meteo.com/v1/archive",
                params=params,
                timeout=60.0,
            )
            if resp.status_code == 429:
                wait = RETRY_BACKOFF * (attempt + 1)
                print(f"    429 限流，等待 {wait}s 后重试 ({attempt + 1}/{MAX_RETRIES})...", file=sys.stderr)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()

            data = resp.json()
            daily = data.get("daily", {})
            temp_max_list = [t for t in daily.get("temperature_2m_max", []) if t is not None]
            temp_min_list = [t for t in daily.get("temperature_2m_min", []) if t is not None]
            precip_list = [p for p in daily.get("precipitation_sum", []) if p is not None]
            wind_list = [w for w in daily.get("wind_speed_10m_max", []) if w is not None]

            if not temp_max_list:
                return _fallback_climate(month)

            avg_max = sum(temp_max_list) / len(temp_max_list)
            avg_min = sum(temp_min_list) / len(temp_min_list) if temp_min_list else avg_max - 8
            avg_temp = (avg_max + avg_min) / 2
            precip_days = sum(1 for p in precip_list if p > 0)
            total_precip = sum(precip_list)
            avg_wind = sum(wind_list) / len(wind_list) if wind_list else 10
            precip_ratio = precip_days / max(len(precip_list), 1)
            sunshine_est = max(4, 10 - precip_ratio * 8) * (1 if month in (5, 6, 7, 8) else 0.7)
            uv_estimates = {1: 2, 2: 3, 3: 4, 4: 6, 5: 7, 6: 9, 7: 9, 8: 8, 9: 6, 10: 4, 11: 3, 12: 2}
            uv = uv_estimates.get(month, 5)
            if lat < 30:
                uv = min(uv + 2, 11)
            elif lat > 45:
                uv = max(uv - 1, 1)

            return {
                "month": month,
                "temp_avg_c": round(avg_temp, 1),
                "temp_max_avg_c": round(avg_max, 1),
                "temp_min_avg_c": round(avg_min, 1),
                "precip_days": round(precip_days / 4, 1),
                "precip_mm": round(total_precip / 4, 1),
                "sunshine_hours": round(sunshine_est, 1),
                "uv_index_avg": uv,
                "wind_speed_avg_kmh": round(avg_wind, 1),
            }
        except httpx.HTTPStatusError as e:
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF * (attempt + 1)
                print(f"    HTTP {e.response.status_code}，等待 {wait}s 后重试 ({attempt + 1}/{MAX_RETRIES})...", file=sys.stderr)
                await asyncio.sleep(wait)
            else:
                print(f"    ✗ month={month} 多次重试失败，使用 fallback", file=sys.stderr)
                return _fallback_climate(month)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF * (attempt + 1)
                print(f"    错误: {e}，等待 {wait}s 后重试 ({attempt + 1}/{MAX_RETRIES})...", file=sys.stderr)
                await asyncio.sleep(wait)
            else:
                print(f"    ✗ month={month} 多次重试失败: {e}，使用 fallback", file=sys.stderr)
                return _fallback_climate(month)

    return _fallback_climate(month)


def load_existing(output_path: Path) -> dict:
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            return json.load(f)
    return {"destinations": []}


def save_output(output_path: Path, data: dict) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def fetch_all(output_path: Path) -> dict:
    existing = load_existing(output_path)
    completed_iatas = {d["iata_code"] for d in existing.get("destinations", []) if len(d.get("monthly_climate", [])) == 12}
    output = existing

    async with httpx.AsyncClient() as client:
        for dest in BASE_DESTINATIONS:
            if dest["iata"] in completed_iatas:
                print(f"  ✓ {dest['city']} 已完成，跳过")
                continue

            print(f"正在获取 {dest['city']}, {dest['state']} 的气候数据...")
            climates = []
            for month in range(1, 13):
                climate = await fetch_monthly_climate(client, dest["lat"], dest["lon"], month)
                climates.append(climate)
                src = "API" if climate != _fallback_climate(month) else "fallback"
                print(f"    month={month:2d} [{src}]")
                await asyncio.sleep(REQUEST_DELAY)

            tz = TIMEZONE_MAP.get(dest["state"], "America/New_York")
            dest_data = {
                "id": dest["id"],
                "city": dest["city"],
                "state": dest["state"],
                "country": "United States",
                "country_code": "US",
                "iata_code": dest["iata"],
                "latitude": dest["lat"],
                "longitude": dest["lon"],
                "timezone": tz,
                "cost_level": dest["cost"],
                "public_transport_score": dest["transit"],
                "walkability_score": dest["walk"],
                "tags": dest["tags"],
                "active": True,
                "monthly_climate": climates,
            }

            existing_ids = [d.get("id") for d in output.get("destinations", [])]
            if dest["id"] in existing_ids:
                idx = existing_ids.index(dest["id"])
                output["destinations"][idx] = dest_data
            else:
                output.setdefault("destinations", []).append(dest_data)

            save_output(output_path, output)
            print(f"  → {dest['city']} 完成（增量保存）")

    return output


def main():
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    output_path = data_dir / "destinations.json"

    print("=== Open-Meteo 气候数据批量拉取 ===")
    print(f"目标文件: {output_path}")
    print(f"请求间隔: {REQUEST_DELAY}s, 重试: {MAX_RETRIES} 次, 退避: {RETRY_BACKOFF}s")
    print()

    start = time.time()
    result = asyncio.run(fetch_all(output_path))
    elapsed = time.time() - start

    real_count = sum(1 for d in result["destinations"] for c in d.get("monthly_climate", []) if c.get("wind_speed_avg_kmh", 0) != 12.0)
    fallback_count = 240 - real_count

    print(f"\n✅ 完成! 已写入 {output_path}")
    print(f"共 {len(result['destinations'])} 个目的地, 耗时 {elapsed:.0f}s")
    print(f"真实数据: {real_count} 条, fallback: {fallback_count} 条")


if __name__ == "__main__":
    main()
