# 系统架构

## 架构原则

1. 确定性系统优先，LLM 只负责解释和生成
2. 单体应用，清晰模块划分
3. 推荐可解释，每个评分有依据
4. Mock 数据优先开发，真实 API 后续接入
5. 所有外部数据标注来源

## 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                      CLI / API 层                        │
│  cli/search.py           api/search.py                  │
└──────────────┬──────────────────────────┬───────────────┘
               │                          │
┌──────────────▼──────────────────────────▼───────────────┐
│                   服务编排层                              │
│  search_orchestrator.py                                  │
│    1. 生成日期组合                                        │
│    2. 筛选候选目的地                                      │
│    3. 查询航班/酒店/天气                                  │
│    4. 硬约束过滤                                          │
│    5. 评分排序                                            │
│    6. 返回 Top 5                                         │
└──────┬──────────┬──────────┬──────────┬─────────────────┘
       │          │          │          │
┌──────▼───┐ ┌───▼────┐ ┌──▼───────┐ ┌▼──────────────┐
│ 日期搜索  │ │ 目的地  │ │ 评分引擎  │ │ 数据服务层     │
│ date_    │ │ dest_  │ │ scoring_ │ │ flight_svc    │
│ search   │ │ filter │ │ service  │ │ hotel_svc     │
│ service  │ │        │ │          │ │ weather_svc   │
└──────────┘ └────────┘ └──────────┘ └───┬───────────┘
                                          │
                              ┌───────────▼───────────┐
                              │     Provider 层        │
                              │  ┌─────────────────┐  │
                              │  │ mock_flight     │  │
                              │  │ mock_hotel      │  │
                              │  │ mock_weather    │  │
                              │  ├─────────────────┤  │
                              │  │ amadeus_flight  │  │
                              │  │ amadeus_hotel   │  │
                              │  │ openmeteo       │  │
                              │  └─────────────────┘  │
                              └───────────┬───────────┘
                                          │
                              ┌───────────▼───────────┐
                              │    缓存层              │
                              │  flight_cache (4h)     │
                              │  hotel_cache (4h)      │
                              │  weather_cache (6h)    │
                              └───────────────────────┘
```

## 数据流

```
用户输入 (CLI/API)
    │
    ▼
SearchRequestSchema
    │
    ▼
generate_date_combinations()  →  [DateCombo, ...]  (约 33 组)
    │
    ▼
filter_candidates()           →  [DestinationInfo, ...]  (约 12-20 个)
    │
    ▼
对每个 (目的地, 日期组合):
    ├── FlightService.search()      → FlightResult
    ├── HotelService.search()       → HotelResult
    ├── WeatherService.get_forecast() → WeatherResult
    ├── check_hard_constraints()    → passed/filtered
    │
    ▼ (仅通过的候选)
ScoringService:
    ├── score_flight()
    ├── score_hotel()
    ├── score_weather()
    ├── score_preference_match()
    ├── score_transport()
    ├── score_activities()
    └── compute_total_score()
    │
    ▼
对每个目的地取最高分日期 → Top 5 → SearchResponse
```

## Provider 接口

```python
class FlightProvider(ABC):
    async def search_flights(origin, destination, depart_date, return_date) -> FlightResult | None
    async def search_cheapest_dates(origin, destination, start_date, end_date) -> list[FlightResult]

class HotelProvider(ABC):
    async def search_hotels(city_iata, check_in, check_out, adults=2) -> HotelResult | None

class WeatherProvider(ABC):
    async def get_forecast(lat, lon, start_date, end_date) -> WeatherResult
    async def get_climate_average(lat, lon, month) -> ClimateAverage | None
```

## Mock 数据策略

| 数据 | 生成规则 | 示例 |
|---|---|---|
| 机票价格 | `0.12 * 距离(英里) + 80` × 季节系数 × (0.85~1.15) | ATL→ORD ≈ $140 |
| 酒店价格 | 按消费水平基价 × 季节系数 × (0.80~1.20) | level 3 ≈ $180/晚 |
| 天气 | 基于目的地月度气候 + 随机偏差 | 9月丹佛: 24°C/12°C |
| 航班时长 | `距离/500 + 0.5h` + 中转时间 | ATL→SFO ≈ 5h |
| 中转次数 | 枢纽机场直飞概率高，小机场中转概率高 | ATL→SFO: 0-1 次 |

## 缓存策略

| 缓存类型 | TTL | Key 格式 |
|---|---|---|
| 航班 | 4 小时 | `flight:{origin}:{dest}:{depart}:{return}` |
| 酒店 | 4 小时 | `hotel:{iata}:{check_in}:{check_out}` |
| 天气 | 6 小时 | `weather:{iata}:{start}:{end}` |

Phase 1 使用内存缓存。Phase 2 迁移到数据库缓存表。

## 评分引擎设计

### 机票评分（score_flight）

价格/预算比率 → 分数映射：
- ratio ≤ 0.4 → 100
- ratio ≤ 0.6 → 90
- ratio ≤ 0.8 → 70
- ratio ≤ 1.0 → 50
- ratio > 1.0 → max(0, 50 - (ratio-1)*100)

### 酒店评分（score_hotel）

用剩余预算（budget - flight_price）计算：
- ratio ≤ 0.4 → 100
- ratio ≤ 0.6 → 90
- ratio ≤ 0.8 → 70
- ratio ≤ 1.0 → 50
- ratio > 1.0 → max(0, 50 - (ratio-1)*100)

### 天气评分（score_weather）

基础分 70，加减分：
- 平均最高温在 18-28°C → +15
- 平均降水概率 < 30% → +10
- avoid_hot_weather 且有 >35°C → -30
- avoid_cold_weather 且有 <5°C → -30

### 偏好匹配评分（score_preference_match）

匹配比例 × 80 + 公共交通额外加分

### 交通便利度评分（score_transport）

`transit_score * 8 + walk_score * 2`
no_car_rental 约束下 transit < 5 → 大幅扣分

### 活动丰富度评分（score_activities）

`min(100, tag_count * 12 + matched * 5)`

### 总分计算

加权求和：30% 机票 + 20% 酒店 + 20% 天气 + 15% 偏好 + 10% 交通 + 5% 活动

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+, FastAPI, Pydantic |
| 数据库 | SQLite (Phase 1), PostgreSQL (后续) |
| ORM | SQLAlchemy 2.0 |
| 外部 API | Amadeus, Open-Meteo |
| CLI | argparse + Rich |
| 测试 | pytest, pytest-asyncio |
| 依赖管理 | uv / pip |
