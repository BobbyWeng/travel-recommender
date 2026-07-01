# Provider 配置指南

## 支持的 Provider

| 领域 | Provider | 类型 | 说明 |
|---|---|---|---|
| 航班 | Mock | 模拟 | 基于距离/季节公式的确定性价格生成 |
| 航班 | Amadeus | 真实 API | OAuth 2.0 认证，支持 Flight Offers 和 Cheapest Date Search |
| 航班 | Duffel | 真实 API | Bearer Token 认证，支持多段航班和完整 offer 详情 |
| 酒店 | Mock | 模拟 | 基于消费水平的确定性价格生成 |
| 酒店 | Amadeus | 真实 API | 按城市/日期搜索酒店价格 |
| 天气 | Mock | 模拟 | 基于月度气候数据 + 随机偏差 |
| 天气 | Open-Meteo | 真实 API | 16 天预报 + 历史气候数据，无需 API Key |

## FLIGHT_PROVIDER 设置

`.env` 中 `FLIGHT_PROVIDER` 控制航班数据源选择：

| 值 | 行为 |
|---|---|
| `auto` | 自动检测：优先 Duffel（如已启用），其次 Amadeus（如已配置），否则 Mock |
| `duffel` | 强制使用 Duffel，未配置时回退到 Mock |
| `amadeus` | 强制使用 Amadeus，未配置时回退到 Mock |
| `mock` | 强制使用 Mock，**生产环境禁止使用** |

选择逻辑见 `backend/app/providers/factory.py:46`。

### auto 模式优先级

1. 若 `DUFFEL_ENABLED=true` 且 `DUFFEL_ACCESS_TOKEN` 非空 → Duffel
2. 若 `AMADEUS_CLIENT_ID` 和 `AMADEUS_CLIENT_SECRET` 非空 → Amadeus
3. 否则 → Mock（仅开发环境）

## Duffel 配置

```env
DUFFEL_ENABLED=true
DUFFEL_ACCESS_TOKEN=duffel_test_xxx     # 从 Duffel Dashboard 获取
DUFFEL_BASE_URL=https://api.duffel.com  # 测试环境用 https://api.duffel.com
DUFFEL_TIMEOUT_SECONDS=30               # 请求超时
DUFFEL_MAX_RETRIES=3                    # 可重试错误的最大重试次数
```

### Duffel 特性

- 自动选择最低价 offer
- 解析完整航班段（segments）、航司、时长
- 指数退避重试（429 限流、5xx 服务端错误）
- 401 认证错误不重试，直接抛出 `ProviderError`
- 返回 `DataKind.LIVE` 标记
- 支持 `FlightOffer` 完整结构（含 expires_at、baggage 等）

## Amadeus 配置

```env
AMADEUS_CLIENT_ID=your_client_id
AMADEUS_CLIENT_SECRET=your_client_secret
AMADEUS_ENV=sandbox          # sandbox 或 production
```

### Amadeus 特性

- 使用 `AmadeusAuthClient` 单例管理 OAuth token（自动刷新，提前 60 秒过期）
- sandbox 环境使用 `test.api.amadeus.com`
- 支持 Flight Offers Search 和 Flight Cheapest Date Search
- 429 限流时静默返回 None（触发 fallback）
- 返回 `DataKind.LIVE` 标记

## Mock vs 生产数据差异

| 维度 | Mock | 生产 API |
|---|---|---|
| 价格 | `0.12 × 距离 + 80` × 季节系数 × ±15% 随机 | 真实市场价 |
| 酒店价格 | 消费等级基价 × 季节系数 × ±20% 随机 | 真实可预订价格 |
| 天气 | 月度气候均值 + 小幅随机偏差 | 实时预报 / 历史数据 |
| 航段详情 | 不提供 segments | 完整航段、航司、机型 |
| offer 可预订 | 否 | 是（含 expires_at） |
| 数据标记 | `DataKind.MOCK` | `DataKind.LIVE` |
| 确定性 | 是（相同 seed 相同结果） | 否 |

## ALLOW_MOCK_FALLBACK 行为

`ALLOW_MOCK_FALLBACK=true`（默认）时，FallbackFlightProvider/FallbackHotelProvider/FallbackWeatherProvider 在主 provider 失败或返回空结果后，自动回退到 Mock provider。

回退时：
- 返回结果的 `source` 标记为 `"mock"`
- `source_metadata.data_kind` 标记为 `DataKind.MOCK`
- `source_metadata.fallback_used` 标记为 `True`
- `source_metadata.fallback_reason` 标记为 `"primary_provider_failed"`

`ALLOW_MOCK_FALLBACK=false` 时：
- 主 provider 失败后返回 `None`/空列表
- 不会调用 Mock provider

### 各环境推荐配置

| 环境 | ALLOW_MOCK_FALLBACK | 说明 |
|---|---|---|
| development | `true` | 无真实 API 也能开发 |
| staging | `true` | 便于测试 fallback 逻辑 |
| production | `false` | 确保数据真实性，避免展示模拟价格 |

## ProviderError 类型

| 错误码 | 可重试 | 触发场景 |
|---|---|---|
| `AUTH_ERROR` | 否 | API 认证失败（401） |
| `RATE_LIMITED` | 是 | API 限流（429） |
| `TIMEOUT` | 是 | 请求超时 |
| `NO_RESULTS` | 否 | API 返回空结果 |
| `INVALID_RESPONSE` | 否 | 响应格式异常 |
| `UPSTREAM_ERROR` | 是 | 上游服务端错误（5xx） |
| `CONFIGURATION_ERROR` | 否 | 配置错误（如生产环境使用 Mock） |

`ProviderError` 结构：

```python
class ProviderError(Exception):
    provider: str           # "duffel" / "amadeus" / "factory"
    code: ProviderErrorCode
    retryable: bool         # 是否可重试
    status_code: int | None # HTTP 状态码
    detail: str | None      # 错误详情
```

## Fallback 行为

所有 provider 通过 `FallbackXxxProvider` 包装，统一回退逻辑：

```
主 Provider 调用
    ├── 成功 → 返回结果
    ├── 返回 None/空 → 检查 ALLOW_MOCK_FALLBACK
    │   ├── true  → 调用 Mock Provider，标记 fallback_used=True
    │   └── false → 返回 None/空
    └── 抛出异常 → 捕获，检查 ALLOW_MOCK_FALLBACK（同上）
```

天气 provider 特殊：`FallbackWeatherProvider` 始终使用 Open-Meteo 作为主 provider，Mock 作为回退，因为 Open-Meteo 无需 API Key。
