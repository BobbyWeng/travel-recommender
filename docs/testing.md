# 测试指南

## 后端测试

### 运行命令

```bash
cd backend && pytest -q
```

运行特定测试文件：

```bash
cd backend && pytest tests/test_duffel_flight.py -q
cd backend && pytest tests/test_search_funnel.py -q
```

运行并显示详细输出：

```bash
cd backend && pytest -v
```

## 前端检查

```bash
cd frontend && npm run lint && npm run build
```

- `lint`：ESLint 代码检查
- `build`：Next.js 生产构建（包含类型检查）

## 测试文件组织

```
backend/tests/
├── __init__.py
├── test_date_search.py              # 日期组合生成
├── test_destination_filter.py       # 目的地预筛选
├── test_destinations_data.py        # 目的地数据验证
├── test_db_cache.py                 # 数据库缓存层
├── test_duffel_flight.py            # Duffel Provider
├── test_mock_providers.py           # Mock Provider
├── test_providers_integration.py    # Provider 集成测试
├── test_scoring.py                  # 评分引擎
├── test_search_funnel.py            # 搜索漏斗三阶段
├── test_search_history.py           # 搜索历史
└── test_search_orchestrator.py      # 搜索编排器
```

## 测试 Fixture

### Duffel Provider Fixture

`test_duffel_flight.py` 中提供 `provider` fixture：

```python
@pytest.fixture
def provider():
    settings.DUFFEL_ACCESS_TOKEN = "test_token"
    settings.DUFFEL_ENABLED = True
    settings.DUFFEL_MAX_RETRIES = 3
    settings.DUFFEL_TIMEOUT_SECONDS = 30
    p = DuffelFlightProvider()
    yield p
    # 恢复原始设置
```

### 搜索漏斗 Fixture

`test_search_funnel.py` 中 `_build_orchestrator()` 构建完整的编排器：

- 使用 `MockFlightProvider`/`MockHotelProvider`/`MockWeatherProvider`
- 从 `data/destinations.json` 加载真实目的地数据
- 清除缓存确保测试隔离

## Duffel Provider 测试（Mock HTTP 响应）

Duffel 测试通过 mock `httpx.AsyncClient` 模拟 HTTP 响应，不发送真实请求。

### 核心 Mock 工具函数

```python
def _make_duffel_response(offers=None)   # 构造 Duffel API 响应
def _make_offer(total_amount, slices)     # 构造单个 offer
def _make_slice(origin, dest, date)       # 构造航班段
def _make_segment(origin, dest, date)     # 构造航班 segment
def _mock_response(status_code, json_data) # 构造 httpx.Response mock
```

### 测试覆盖的场景

| 测试类 | 场景 |
|---|---|
| `TestDuffelNormalRoundTrip` | 直飞往返正常响应 |
| `TestDuffelMultiSegment` | 多段航班（经停） |
| `TestDuffelEmptyResults` | 无可用 offer |
| `TestDuffelRateLimitedRetry` | 429 限流后重试成功 |
| `TestDuffelAuthError` | 401 认证错误不重试 |
| `TestDuffelServerError` | 5xx 错误重试后失败 |
| `TestDuffelTimeout` | 请求超时抛出 ProviderError |
| `TestDuffelMalformedJson` | 响应格式异常 |
| `TestDuffelExpiresAt` | offer 过期时间解析 |
| `TestDuffelDecimalPrice` | Decimal 价格精度 |
| `TestDuffelSourceMetadata` | 数据来源标记正确性 |
| `TestDuffelCheapestSelection` | 选择最低价 offer |
| `TestDuffelSearchCheapestDates` | 最便宜日期搜索 |

### Mock HTTP 请求模式

```python
with patch("httpx.AsyncClient") as mock_client_cls:
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.request = AsyncMock(return_value=mock_resp)
    mock_client_cls.return_value = mock_client

    result = await provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))
```

## 搜索漏斗测试

`test_search_funnel.py` 验证三阶段搜索行为：

| 测试 | 验证内容 |
|---|---|
| `test_stage1_no_external_api_calls` | Stage 1 不调用任何 provider |
| `test_stage2_uses_limited_date_samples` | Stage 2 限制日期采样数 |
| `test_budget_not_exceeded` | provider 调用不超预算 |
| `test_results_sorted_by_score` | 结果按评分降序排列 |
| `test_execution_stats_populated` | 执行统计正确填充 |
| `test_60_cities_limited_candidates_queried` | 候选数不超过配置上限 |
| `test_cache_hit_on_second_search` | 二次搜索命中缓存 |
| `test_low_budget_no_results_with_funnel` | 低预算无结果 |

## 数据验证脚本

验证目的地数据完整性和格式：

```bash
python scripts/validate_destinations.py
```

检查内容：
- 目的地数量在 55-65 范围内
- ID / IATA 代码唯一性
- 必填字段完整性
- 坐标、消费水平、评分范围合法性
- 标签有效性
- 月度气候数据 12 个月齐全
- 时区格式
- gateway_airports 包含主 IATA 代码
