# Phase 1 报告：技术验证与基础实现

## 完成状态

| 任务 | 状态 | 说明 |
|---|---|---|
| 项目目录结构 | ✅ 完成 | 完整的 backend/app/ 目录，含 core, models, schemas, providers, services, repositories, api |
| API 调研评估 | ✅ 完成 | 航班(Amadeus)、酒店(Amadeus)、天气(Open-Meteo)、地理(GeoNames) |
| 数据模型设计 | ✅ 完成 | SQLAlchemy 模型 + Pydantic Schema |
| 候选目的地数据集 | ✅ 完成 | 20 个美国城市，12 个月气候数据 |
| Mock Provider | ✅ 完成 | 机票/酒店/天气三个 Mock Provider |
| 核心服务实现 | ✅ 完成 | 日期搜索、目的地筛选、评分引擎、服务编排 |
| CLI 入口 | ✅ 完成 | argparse + Rich 格式化输出 |
| 单元测试 | ✅ 完成 | 46 个测试，全部通过 |
| 文档 | ✅ 完成 | product_scope, api_evaluation, system_architecture, data_model |

## API 验证结果

### Open-Meteo Historical API

- **成功获取** 17/20 个城市的气候数据（2020-2023 年平均）
- **限流发现**：免费层约 600 请求/分钟，但持续大量请求会触发 429
- **实际延迟**：需要 6-10 秒间隔才能稳定拉取
- **3 个城市用公开数据补充**：Phoenix, Minneapolis, Atlanta

### Amadeus / OpenWeatherMap

- 未在 Phase 1 接入真实 API（按计划先做 Mock）
- API 评估基于文档研究，选型确认

## 运行验证

### CLI 运行示例

```bash
python backend/cli/search.py \
    --origin ATL --date 2026-09-20 --flex 5 \
    --min-nights 4 --max-nights 6 --budget 1500 \
    --preferences nature food public_transport \
    --max-flight-hours 8 --max-stops 1 \
    --avoid-hot-weather --no-car-rental
```

**输出：**
- 评估了 396 个候选（20 目的地 × ~20 日期组合）
- 过滤了 97 个不满足硬约束的
- 返回 Top 5 推荐，带完整评分

### 测试结果

```
46 passed in 0.18s
```

覆盖：
- 日期组合生成：7 个测试
- 目的地筛选：10 个测试
- 评分引擎：15 个测试
- Mock Provider：8 个测试
- 端到端搜索：6 个测试

## 关键发现

### 1. Open-Meteo 限流比预期严格

免费层声称 10,000 调用/天，但实际在短时间内的并发请求会被限流。建议：
- 正式使用时每请求间隔 ≥ 2 秒
- 气候数据一次性拉取后缓存到本地（已完成）
- 考虑自托管 Open-Meteo 消除限流

### 2. Mock 数据需要基于真实气候

初期设计用固定公式生成天气，会导致所有目的地天气相似。改进为：
- 从 Open-Meteo 拉取每个城市 12 个月的气候统计
- Mock Weather Provider 基于这些真实气候数据 + 随机偏差
- 这样不同目的地的天气评分有真实差异

### 3. 评分引擎需要仔细调优

当前评分函数基本合理，但：
- 天气评分的加减分逻辑需要根据实际数据调优
- 偏好匹配评分权重可能需要根据用户反馈调整
- 硬约束阈值（如"炎热"= 35°C）需要可配置

### 4. 搜索复杂度控制

20 个目的地 × 33 个日期组合 = 660 次查询（航班+酒店+天气各一次）。Mock 模式下很快，真实 API 下需要：
- 使用 Amadeus Inspiration Search 一次查询多个目的地
- 并行化不同目的地的查询
- 实现更智能的缓存策略

## 未完成事项

| 事项 | 原因 | 计划 |
|---|---|---|
| 真实 API 探针脚本 | 优先完成 Mock + CLI | Phase 2 初期 |
| FastAPI 后端 API | CLI 先行 | Phase 3 |
| 数据库初始化脚本 | 当前用 JSON 文件 | Phase 2（接入 SQLAlchemy） |
| Web 前端 | Phase 4 | 依赖后端 API |
| LLM 接入 | Phase 5 | 依赖推荐引擎稳定 |

## 下一步：Phase 2（无 LLM 的推荐 MVP）

### 目标

接入真实 API，完成可实际运行的推荐闭环。

### 任务

1. 实现 Amadeus Provider（航班 + 酒店）
2. 实现 Open-Meteo Provider（天气预报 + 气候查询）
3. 数据库初始化（加载 destinations.json 到 SQLite）
4. 实现缓存持久化（从内存缓存迁移到数据库缓存表）
5. FastAPI 后端 API
   - `POST /search` - 发起搜索
   - `GET /search/{id}` - 获取结果
   - `GET /destinations` - 目的地列表
6. API 失败降级逻辑（真实 API 失败时回退到 Mock）
7. 并行化查询（asyncio.gather）
8. 集成测试（真实 API）

### 预计时间

8-12 小时

## 项目文件总览

```
travel-recommender/
├── .env.example
├── backend/
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── app/
│   │   ├── core/config.py           # Pydantic Settings
│   │   ├── core/cache.py            # 内存缓存
│   │   ├── models/destination.py    # SQLAlchemy 模型
│   │   ├── schemas/search.py        # Pydantic Schema
│   │   ├── providers/base.py        # 抽象接口
│   │   ├── providers/mock_flight.py # Mock 航班
│   │   ├── providers/mock_hotel.py  # Mock 酒店
│   │   ├── providers/mock_weather.py# Mock 天气
│   │   ├── services/date_search_service.py
│   │   ├── services/destination_service.py
│   │   ├── services/scoring_service.py
│   │   ├── services/flight_service.py
│   │   ├── services/hotel_service.py
│   │   ├── services/weather_service.py
│   │   └── services/search_orchestrator.py
│   ├── cli/search.py               # CLI 入口
│   └── tests/                      # 46 个测试
├── data/destinations.json          # 20 个美国城市 + 12 月气候
├── scripts/fetch_climate_data.py   # Open-Meteo 数据拉取脚本
└── docs/
    ├── product_scope.md
    ├── api_evaluation.md
    ├── system_architecture.md
    ├── data_model.md
    └── phase_1_report.md
```
