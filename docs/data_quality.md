# 数据质量与来源标记

## DataKind 枚举

每个数据字段标注其数据来源类型：

| 值 | 含义 | 典型场景 |
|---|---|---|
| `LIVE` | 实时数据 | Amadeus/Duffel 实时航班搜索、Open-Meteo 实时预报 |
| `CACHED` | 缓存数据 | 命中 SQLite 缓存的航班/酒店价格 |
| `HISTORICAL` | 历史数据 | Open-Meteo 历史气候平均 |
| `ESTIMATED` | 估算数据 | 基于模型的天气推断 |
| `MOCK` | 模拟数据 | Mock Provider 生成的确定性模拟数据 |
| `UNAVAILABLE` | 数据不可用 | Provider 返回空或异常 |

定义见 `backend/app/schemas/search.py:8`。

## SourceMetadata 结构

```python
class SourceMetadata(BaseModel):
    provider: str                        # 数据源名称："amadeus"/"duffel"/"mock"/"openmeteo"
    data_kind: DataKind                  # 数据类型
    fetched_at: datetime | None = None   # 数据获取时间
    expires_at: datetime | None = None   # 数据过期时间（offer 有效期）
    cache_hit: bool = False              # 是否命中缓存
    fallback_used: bool = False          # 是否使用了 fallback
    fallback_reason: str | None = None   # fallback 原因
```

### 各 Provider 设置方式

| Provider | provider 值 | data_kind | 特殊标记 |
|---|---|---|---|
| MockFlight | `"mock"` | `MOCK` | — |
| MockHotel | `"mock"` | `MOCK` | — |
| MockWeather | `"mock"` | `MOCK` | — |
| AmadeusFlight | `"amadeus"` | `LIVE` | — |
| AmadeusHotel | `"amadeus"` | `LIVE` | — |
| DuffelFlight | `"duffel"` | `LIVE` | offer 含 `expires_at`、`fetched_at` |
| OpenMeteoWeather | `"openmeteo"` | `LIVE`/`HISTORICAL` | 16 天内用预报(LIVE)，超出用气候(HISTORICAL) |
| Fallback 回退 | `"mock"` | `MOCK` | `fallback_used=True`，`fallback_reason="primary_provider_failed"` |

## DataQualitySummary 结构

```python
class DataQualitySummary(BaseModel):
    completeness: float = 0.0            # 数据完整度 (0-1)，可用字段/3
    live_field_count: int = 0            # LIVE 字段数
    cached_field_count: int = 0          # CACHED 字段数
    historical_field_count: int = 0      # HISTORICAL 字段数
    estimated_field_count: int = 0       # ESTIMATED 字段数
    mock_field_count: int = 0            # MOCK 字段数
    unavailable_field_count: int = 0     # UNAVAILABLE 字段数
```

计算逻辑（`SearchOrchestrator._compute_data_quality`）：

1. 对航班、酒店、天气三个结果逐一检查 `source_metadata.data_kind`
2. 按类型累加计数
3. `completeness = available_fields / 3.0`

## ScoredDestination 中的数据来源字段

```python
class ScoredDestination(BaseModel):
    data_source: str = "unknown"               # 所有来源拼接，如 "amadeus+mock+openmeteo"
    flight_data_kind: DataKind | None = None   # 航班数据类型
    hotel_data_kind: DataKind | None = None    # 酒店数据类型
    weather_data_kind: DataKind | None = None  # 天气数据类型
    data_quality: DataQualitySummary | None = None
```

## Provider 如何设置 DataKind

### 真实 API Provider

```python
# Amadeus/Duffel：返回 LIVE
source_metadata=SourceMetadata(provider="amadeus", data_kind=DataKind.LIVE)
source_metadata=SourceMetadata(provider="duffel", data_kind=DataKind.LIVE)
```

### Mock Provider

```python
# Mock：返回 MOCK
source_metadata=SourceMetadata(provider="mock", data_kind=DataKind.MOCK)
```

### Fallback Provider

```python
# 主 provider 失败后回退到 Mock
source_metadata=SourceMetadata(
    provider="mock",
    data_kind=DataKind.MOCK,
    fallback_used=True,
    fallback_reason="primary_provider_failed",
)
```

### Open-Meteo 天气

```python
# 16 天内预报
source_metadata=SourceMetadata(provider="openmeteo", data_kind=DataKind.LIVE)

# 超出预报范围，使用气候数据
source_metadata=SourceMetadata(provider="openmeteo", data_kind=DataKind.HISTORICAL)
```

## 前端数据来源展示

前端应根据 `data_quality` 和 `xxx_data_kind` 字段向用户展示数据来源信息：

| 展示场景 | 数据条件 | 建议展示 |
|---|---|---|
| 价格可靠 | `live_field_count ≥ 2` | 正常展示，可标注"实时价格" |
| 部分模拟 | `mock_field_count ≥ 1` | 标注"部分价格为估算值" |
| 完全模拟 | `mock_field_count == 3` | 明确标注"所有数据为模拟" |
| 天气历史 | `weather_data_kind == HISTORICAL` | 标注"基于历史气候数据" |
| 数据不完整 | `completeness < 1.0` | 提示部分数据不可用 |

## Mock 数据标记要求

所有 Mock Provider 必须遵守以下标记规则：

1. `source` 字段必须为 `"mock"`
2. `source_metadata.provider` 必须为 `"mock"`
3. `source_metadata.data_kind` 必须为 `DataKind.MOCK`
4. 通过 Fallback 回退到 Mock 时，额外标记 `fallback_used=True`
5. Mock 数据**不得**标记为 `LIVE` 或 `HISTORICAL`
6. 前端不得将 Mock 数据展示为实时价格
