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
                               │  │ duffel_flight   │  │
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

## Provider 架构与 Fallback 链

```
FlightService
    └── FallbackFlightProvider
            ├── Primary: Duffel / Amadeus / Mock（由 FLIGHT_PROVIDER 决定）
            └── Fallback: MockFlightProvider（ALLOW_MOCK_FALLBACK 控制是否启用）

HotelService
    └── FallbackHotelProvider
            ├── Primary: AmadeusHotelProvider（如已配置）
            └── Fallback: MockHotelProvider

WeatherService
    └── FallbackWeatherProvider
            ├── Primary: OpenMeteoWeatherProvider（始终启用）
            └── Fallback: MockWeatherProvider
```

Provider 选择逻辑（`factory.py:46`）：

| FLIGHT_PROVIDER | DUFFEL_ENABLED | Amadeus 配置 | 实际 Provider |
|---|---|---|---|
| `auto` | true + token | — | Duffel + Mock fallback |
| `auto` | false | 已配置 | Amadeus + Mock fallback |
| `auto` | false | 未配置 | Mock（仅开发环境） |
| `duffel` | — | — | Duffel + Mock fallback |
| `amadeus` | — | — | Amadeus + Mock fallback |
| `mock` | — | — | Mock（生产环境抛异常） |

Fallback 行为：主 Provider 失败/返回空 → 检查 `ALLOW_MOCK_FALLBACK` → 启用则回退到 Mock 并标记 `fallback_used=True`，否则返回 None。详见 [providers.md](providers.md)。

### AmadeusAuthClient 单例

`AmadeusAuthClient` 使用单例模式管理 OAuth 2.0 token：

- `get_instance()` 返回全局唯一实例
- `get_access_token()` 使用双重检查锁（double-checked locking）保证并发安全
- Token 提前 60 秒过期，自动刷新
- sandbox 环境使用 `test.api.amadeus.com`

```python
class AmadeusAuthClient:
    _instance: AmadeusAuthClient | None = None
    _lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> AmadeusAuthClient: ...

    async def get_access_token(self) -> str: ...
```

## 缓存分层

```
请求 → 内存缓存(LRU) → SQLite 缓存表 → Provider API
          │                    │
          │ 命中 → 直接返回     │ 命中 → 更新内存缓存 → 返回
          │                    │ 未命中 → 调用 API → 写入两层缓存 → 返回
          ▼                    ▼
     Key: flight:{origin}:{dest}:{depart}:{return}
     Key: hotel:{iata}:{check_in}:{check_out}
     Key: weather:{iata}:{start}:{end}
```

| 层 | 介质 | TTL | 说明 |
|---|---|---|---|
| L1 | 内存 (dict) | 航班 4h / 酒店 4h / 天气 6h | 进程内快速访问 |
| L2 | SQLite 表 | 同上 | 持久化，跨进程共享 |

缓存命中时 `source_metadata.cache_hit = True`，`data_kind = CACHED`。

## 搜索漏斗架构

详见 [search_pipeline.md](search_pipeline.md)。

```
全部目的地 (20-60)
    │ Stage 1: 离线预筛选（0 次 API 调用）
    ▼
候选目的地 (≤20)
    │ Stage 2: 代表性日期粗搜（有限 API 调用）
    ▼
评分候选 (≤8)
    │ Stage 3: 细粒度日期搜索
    ▼
Top 5 推荐
```

`SearchExecutionBudget` 控制每阶段上限，`SearchExecutionStats` 记录执行统计。

## 数据来源模型

详见 [data_quality.md](data_quality.md)。

每个结果携带 `SourceMetadata`（provider、data_kind、cache_hit、fallback_used）和 `DataQualitySummary`（各类型字段计数、完整度）。

| DataKind | 含义 |
|---|---|
| `LIVE` | 实时 API 数据 |
| `CACHED` | 缓存命中 |
| `HISTORICAL` | 历史气候数据 |
| `ESTIMATED` | 估算数据 |
| `MOCK` | 模拟数据 |
| `UNAVAILABLE` | 数据不可用 |

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+, FastAPI, Pydantic |
| 数据库 | SQLite (Phase 1), PostgreSQL (后续) |
| ORM | SQLAlchemy 2.0 |
| 外部 API | Amadeus, Duffel, Open-Meteo |
| CLI | argparse + Rich |
| 测试 | pytest, pytest-asyncio |
| 依赖管理 | uv / pip |

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
