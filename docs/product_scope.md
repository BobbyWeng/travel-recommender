# AI 旅行目的地推荐系统 - 产品范围

## 产品定义

一个自动推荐旅行目的地和行程的系统。用户只需提供出发地、出行日期、预算和偏好，系统即可自动筛选、评分和推荐最佳目的地。

## 目标用户

- 不确定去哪旅行的用户
- 希望在预算内找到最优目的地的用户
- 需要灵活日期安排的用户

## 核心功能（MVP）

1. 输入：出发地、日期范围、旅行时长、预算、偏好、约束
2. 输出：Top 5 推荐目的地，含评分、价格、天气、优缺点
3. 每个推荐附带最佳日期组合
4. 所有评分可解释

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| origin | string | 是 | 出发机场 IATA 代码 |
| preferred_departure_date | date | 是 | 首选出发日期 |
| date_flexibility_days | int | 否 | 日期浮动范围（默认 0） |
| trip_length_min | int | 是 | 最短旅行天数 |
| trip_length_max | int | 是 | 最长旅行天数 |
| budget | float | 是 | 总预算（USD） |
| preferences | string[] | 否 | 旅行偏好标签 |
| max_flight_hours | int | 否 | 最大飞行时间 |
| max_stops | int | 否 | 最大中转次数 |
| avoid_hot_weather | bool | 否 | 避免炎热天气 |
| avoid_cold_weather | bool | 否 | 避免寒冷天气 |
| no_car_rental | bool | 否 | 不租车 |

## 输出格式

每个推荐目的地包含：
- 城市名称、州
- 最佳出发/返程日期
- 机票价格、酒店价格、预计总花费
- 天气概况
- 总分（0-100）
- 分项评分：机票、酒店、天气、偏好匹配、交通、活动
- 优点列表
- 缺点列表
- 推荐理由

## 评分权重（默认）

| 维度 | 权重 |
|---|---|
| 机票价格 | 30% |
| 酒店价格 | 20% |
| 天气 | 20% |
| 偏好匹配 | 15% |
| 交通便利度 | 10% |
| 活动丰富度 | 5% |

## 硬约束（不满足直接淘汰）

- 总费用超过预算
- 飞行时间超过上限
- 中转次数超过上限
- 天气不符合要求（如 avoid_hot_weather 且有 >35°C 的日子）
- 需要租车但用户不愿租车（公共交通评分 < 5）

## 候选目的地范围

- Phase 1：20 个美国城市
- 后续：扩展至北美、加勒比、欧洲

## 旅行偏好标签

beach, nature, food, city, museum, nightlife, relaxation, hiking, public_transport, family, budget, music, history, coffee, outdoor, skiing, architecture, art, movie, entertainment, golf, shopping, quirky

## 不在 MVP 范围内

- 用户账户和登录
- 在线支付和预订
- 实时航班预订
- 多城市行程
- LLM 自然语言交互（Phase 3）
- 详细行程生成（Phase 4）
- 历史价格追踪（Phase 6）
