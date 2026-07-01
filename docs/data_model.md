# 数据模型

## 实体关系图

```
destinations ──1:N── destination_tags
       │
       └──1:N── destination_monthly_climate

airports (独立)

flight_search_cache (独立)
hotel_search_cache (独立)

search_requests ──1:N── search_candidates

generated_itineraries (Phase 4)
```

## 表结构

### destinations

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | 自增主键 |
| city | VARCHAR(100) | NOT NULL | 城市名 |
| state | VARCHAR(50) | NOT NULL | 州缩写 |
| country | VARCHAR(100) | NOT NULL | 国家 |
| country_code | VARCHAR(2) | NOT NULL | ISO 国家代码 |
| iata_code | VARCHAR(3) | NOT NULL | 主要机场 IATA |
| latitude | FLOAT | NOT NULL | 纬度 |
| longitude | FLOAT | NOT NULL | 经度 |
| timezone | VARCHAR(50) | NOT NULL | 时区 |
| cost_level | INTEGER | NOT NULL | 消费水平 1-5 |
| public_transport_score | INTEGER | NOT NULL | 公共交通评分 1-10 |
| walkability_score | INTEGER | NOT NULL | 步行友好度 1-10 |
| active | BOOLEAN | DEFAULT TRUE | 是否启用 |

### destination_tags

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | 自增主键 |
| destination_id | INTEGER | FK → destinations | 关联目的地 |
| tag | VARCHAR(50) | NOT NULL | 标签名 |

UNIQUE(destination_id, tag)

### destination_monthly_climate

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | 自增主键 |
| destination_id | INTEGER | FK → destinations | 关联目的地 |
| month | INTEGER | NOT NULL | 月份 1-12 |
| temp_avg_c | FLOAT | | 平均温度 |
| temp_max_avg_c | FLOAT | | 平均最高温 |
| temp_min_avg_c | FLOAT | | 平均最低温 |
| precip_days | FLOAT | | 平均降水天数 |
| precip_mm | FLOAT | | 平均降水量 mm |
| sunshine_hours | FLOAT | | 平均日照时数 |
| uv_index_avg | FLOAT | | 平均 UV 指数 |
| wind_speed_avg_kmh | FLOAT | | 平均风速 km/h |

UNIQUE(destination_id, month)

### airports

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| iata_code | VARCHAR(3) | PK | IATA 代码 |
| name | VARCHAR(200) | NOT NULL | 机场名 |
| city | VARCHAR(100) | NOT NULL | 城市 |
| state | VARCHAR(50) | NOT NULL | 州 |
| country_code | VARCHAR(2) | NOT NULL | 国家代码 |
| latitude | FLOAT | NOT NULL | 纬度 |
| longitude | FLOAT | NOT NULL | 经度 |
| is_hub | BOOLEAN | DEFAULT FALSE | 是否枢纽机场 |

### flight_search_cache

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | 自增主键 |
| origin | VARCHAR(3) | NOT NULL | 出发机场 |
| destination | VARCHAR(3) | NOT NULL | 目的机场 |
| departure_date | DATE | NOT NULL | 出发日期 |
| return_date | DATE | NOT NULL | 返程日期 |
| provider | VARCHAR(50) | NOT NULL | 数据源 |
| price | FLOAT | | 价格 |
| currency | VARCHAR(3) | DEFAULT 'USD' | 货币 |
| stops | INTEGER | | 中转次数 |
| total_duration_min | INTEGER | | 总飞行时间(分钟) |
| airline | VARCHAR(100) | | 航空公司 |
| observed_at | TIMESTAMP | NOT NULL | 观察时间 |
| expires_at | TIMESTAMP | NOT NULL | 过期时间 |
| raw_response | TEXT | | 原始响应 |

### hotel_search_cache

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | 自增主键 |
| destination_iata | VARCHAR(3) | NOT NULL | 目的地机场代码 |
| check_in | DATE | NOT NULL | 入住日期 |
| check_out | DATE | NOT NULL | 退房日期 |
| provider | VARCHAR(50) | NOT NULL | 数据源 |
| nightly_price | FLOAT | | 每晚价格 |
| total_price | FLOAT | | 总价 |
| currency | VARCHAR(3) | DEFAULT 'USD' | 货币 |
| hotel_class | FLOAT | | 酒店星级 |
| area | VARCHAR(100) | | 区域 |
| observed_at | TIMESTAMP | NOT NULL | 观察时间 |
| expires_at | TIMESTAMP | NOT NULL | 过期时间 |
| raw_response | TEXT | | 原始响应 |

### search_requests

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | VARCHAR(36) | PK | UUID |
| origin | VARCHAR(3) | NOT NULL | 出发机场 |
| preferred_departure_date | DATE | NOT NULL | 首选出发日期 |
| date_flexibility_days | INTEGER | NOT NULL | 日期浮动天数 |
| trip_length_min | INTEGER | NOT NULL | 最短旅行天数 |
| trip_length_max | INTEGER | NOT NULL | 最长旅行天数 |
| budget | FLOAT | NOT NULL | 预算 |
| currency | VARCHAR(3) | DEFAULT 'USD' | 货币 |
| preferences | TEXT | | JSON 偏好数组 |
| constraints | TEXT | | JSON 约束对象 |
| status | VARCHAR(20) | DEFAULT 'pending' | 状态 |
| created_at | TIMESTAMP | | 创建时间 |
| completed_at | TIMESTAMP | | 完成时间 |

### search_candidates

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | 自增主键 |
| search_id | VARCHAR(36) | FK → search_requests | 关联搜索 |
| destination_id | INTEGER | FK → destinations | 关联目的地 |
| departure_date | DATE | NOT NULL | 出发日期 |
| return_date | DATE | NOT NULL | 返程日期 |
| flight_price | FLOAT | | 机票价格 |
| hotel_price | FLOAT | | 酒店价格 |
| estimated_total | FLOAT | | 预计总花费 |
| flight_score | FLOAT | | 机票评分 |
| hotel_score | FLOAT | | 酒店评分 |
| weather_score | FLOAT | | 天气评分 |
| preference_score | FLOAT | | 偏好匹配评分 |
| transport_score | FLOAT | | 交通评分 |
| activity_score | FLOAT | | 活动评分 |
| total_score | FLOAT | | 总分 |
| passed_constraints | BOOLEAN | | 是否通过约束 |
| recommendation_reason | TEXT | | 推荐理由 |
| warnings | TEXT | | 警告信息 |

## 索引策略

```sql
CREATE INDEX idx_dest_iata ON destinations(iata_code);
CREATE INDEX idx_dest_active ON destinations(active);
CREATE INDEX idx_tag_dest ON destination_tags(destination_id);
CREATE INDEX idx_climate_dest_month ON destination_monthly_climate(destination_id, month);
CREATE INDEX idx_flight_cache_route ON flight_search_cache(origin, destination, departure_date, return_date);
CREATE INDEX idx_hotel_cache ON hotel_search_cache(destination_iata, check_in, check_out);
CREATE INDEX idx_candidate_search ON search_candidates(search_id);
CREATE INDEX idx_candidate_score ON search_candidates(total_score DESC);
```

## 数据文件：destinations.json

包含 20 个美国城市的完整数据，每个城市 12 个月的气候统计。

数据来源：
- 17 个城市：Open-Meteo Historical API（2020-2023 年平均）
- 3 个城市（Phoenix, Minneapolis, Atlanta）：公开气候数据手动编写

所有数据标记了来源，Mock Provider 数据额外标记 `"source": "mock"`。
