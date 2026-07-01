# 搜索管道

## 三阶段搜索漏斗

搜索过程分为三个阶段，逐层收窄候选范围，在保证结果质量的同时控制 API 调用量。

```
全部目的地 (20-60)
    │
    ▼ Stage 1: 离线预筛选（无 API 调用）
候选目的地 (≤20)
    │
    ▼ Stage 2: 代表性日期粗搜
评分候选 (≤8)
    │
    ▼ Stage 3: 细粒度日期搜索
Top 5 推荐
```

### Stage 1: 离线候选预筛选

**无 API 调用**，仅使用本地数据。

`DestinationService.pre_score_candidates()` 根据以下维度对目的地评分：

| 维度 | 权重 | 数据来源 |
|---|---|---|
| 气候适宜度 | — | 目的地月度气候表 |
| 偏好匹配度 | — | 目的地标签 |
| 交通便利度 | — | 目的地公共交通/步行评分 |
| 可负担性 | — | 目的地消费水平 + 用户预算 |
| 距离因素 | — | 出发地与目的地距离 |

- 输出 `CandidatePreScore` 列表，按 `total_score` 降序排列
- 取前 `max_stage1_candidates`（默认 20）个
- 可提前过滤：消费水平远超预算、偏好完全不匹配等

实现见 `backend/app/services/destination_service.py`。

### Stage 2: 代表性日期粗搜

对 Stage 1 产出的每个候选目的地，选取**代表性日期组合**进行航班/酒店/天气查询。

代表性日期选取策略（`_select_representative_dates`）：

1. 首选出发日期
2. 最早可出发日期
3. 最晚可出发日期
4. 工作日出发日期
5. 周末出发日期
6. 等间距补充采样

最多选取 `max_stage2_date_samples`（默认 5）个日期组合。

对每个（目的地, 日期组合）：
- 并发调用航班/酒店/天气 provider
- 硬约束过滤（预算、中转次数、极端天气等）
- 评分计算

按目的地取最高分结果，取前 `max_stage2_candidates`（默认 8）个进入 Stage 3。

### Stage 3: 细粒度日期搜索

对 Stage 2 的 Top 候选，搜索**剩余日期组合**：

- 排除 Stage 2 已搜索的日期
- 对剩余组合采样（超过 10 个时按步长采样）
- 对每个新组合执行完整的航班/酒店/天气查询 + 评分
- 与 Stage 2 最佳结果比较，保留更高分

最终按 `total_score` 降序取 Top 5 返回。

## SearchExecutionBudget

```python
class SearchExecutionBudget(BaseModel):
    max_provider_calls: int = 300      # 最大 provider 调用次数
    max_stage1_candidates: int = 20    # Stage 1 最大候选数
    max_stage2_candidates: int = 8     # Stage 2 最大候选数
    max_stage2_date_samples: int = 5   # Stage 2 每个目的地最大采样日期数
    max_concurrency: int = 8           # 最大并发数
```

- `max_provider_calls`：全局计数器，每次航班/酒店/天气调用各计 1 次
- 超出预算后 Stage 2/3 停止搜索新候选

## SearchExecutionStats

搜索完成后返回的执行统计：

```python
class SearchExecutionStats(BaseModel):
    stage1_candidates: int = 0     # Stage 1 候选数
    stage2_candidates: int = 0     # Stage 2 候选数
    stage3_candidates: int = 0     # Stage 3 候选数
    provider_calls: int = 0        # 实际 provider 调用次数
    cache_hits: int = 0            # 缓存命中次数
    provider_failures: int = 0     # provider 失败次数
    fallback_count: int = 0        # 回退到 mock 的次数
    elapsed_ms: int = 0            # 总耗时（毫秒）
    budget_exhausted: bool = False # 是否耗尽预算
```

## 并发控制

使用 `asyncio.Semaphore(max_concurrency)` 控制并发请求数：

- 航班、酒店、天气三个查询通过 `asyncio.gather()` 并发执行
- Semaphore 限制同时进行的组合查询数量
- 默认并发数 8，避免触发 API 限流

```python
semaphore = asyncio.Semaphore(self._budget.max_concurrency)

async with semaphore:
    flight, hotel, weather = await self._fetch_data_parallel(...)
```

## 预算耗尽处理

当 `provider_calls` 达到 `max_provider_calls` 时：

1. 设置 `budget_exhausted = True`
2. Stage 2 停止搜索新目的地
3. Stage 3 保留 Stage 2 的最佳结果
4. `SearchExecutionStats.budget_exhausted` 返回 `True`
5. 已获取的结果正常评分和排序

预算检查在两个位置执行：
- 进入组合处理前（快速检查）
- 获取 Semaphore 后（并发安全检查）

## 数据并行获取

每个（目的地, 日期组合）的三个数据查询并发执行：

```python
results = await asyncio.gather(
    flight_task, hotel_task, weather_task,
    return_exceptions=True,
)
```

- 任一查询失败不影响其他查询
- 异常被捕获后返回 `None`，不中断整体搜索
- 失败的 provider 会被 Fallback 层处理
