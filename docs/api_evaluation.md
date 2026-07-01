# API 评估报告

## 航班 API

### 推荐：Amadeus for Developers

| 特性 | 详情 |
|---|---|
| 官网 | https://developers.amadeus.com |
| 免费额度 | 10,000 API 调用/月 |
| 付费定价 | ~$0.004/调用 |
| 覆盖范围 | 400+ 航空公司，全球航线 |
| 认证方式 | OAuth 2.0 (client_credentials) |
| SDK | Python, Node.js, Java, PHP |
| 注册 | 自助注册，即时可用 |

**核心端点：**
- `Flight Offers Search` - 实时航班搜索
- `Flight Inspiration Search` - 从出发地搜索最低票价到任意目的地（"去哪儿"功能）
- `Flight Cheapest Date Search` - 指定路线的最便宜日期搜索

**为什么选 Amadeus：**
1. Inspiration Search 和 Cheapest Date Search 是推荐系统的关键端点，1 次调用可获取多日期/目的地价格
2. 10K 免费调用/月足够开发和测试
3. Python SDK 完备
4. 数据质量高（GDS 直连）

**备选：Kiwi/Tequila**
- 优势：虚拟联程（组合廉价航空），Nomad API
- 劣势：文档较粗糙，门户不稳定

## 酒店 API

### 推荐：Amadeus Hotel Search

| 特性 | 详情 |
|---|---|
| 免费额度 | 与航班共享 10,000 调用/月 |
| 覆盖范围 | 150,000+ 酒店，200+ 国家 |
| 数据类型 | 实时价格，可预订 |
| 搜索方式 | 按城市代码 + 日期 |

**核心端点：**
- `Hotel Offers Search` - 按城市和日期搜索酒店价格
- `Hotel Offers by Hotel` - 按酒店 ID 搜索

**局限：**
- 主要是 GDS 酒店数据（连锁酒店为主）
- 缺少廉价/独立酒店
- 无专门的最便宜日期搜索端点

**后续可加入：Hotelbeds Cache API**
- 30 万+ 酒店，每小时批量价格快照
- 佣金制收费（搜索免费）
- 适合价格比较和历史追踪

## 天气 API

### 推荐：Open-Meteo（主）+ OpenWeatherMap（辅）

#### Open-Meteo

| 特性 | 详情 |
|---|---|
| 官网 | https://open-meteo.com |
| 免费 | 10,000 调用/天，无需 API Key |
| 预报范围 | 16 天 |
| 历史数据 | 1940 年至今 |
| 许可 | CC BY 4.0（非商用免费） |
| 自托管 | 开源 AGPLv3 |

**关键能力：**
- 预报 API：温度、降水概率、风速、UV 指数
- 历史 API：用于计算月度气候平均值
- 气候 API：CMIP6 模型数据（1950-2050）

**注意：** 免费版仅限非商用。本项目为个人项目，可直接使用。正式商用需订阅或自托管。

**实测发现：** Open-Meteo 限流较严格（约 600 请求/分钟），批量拉取时需要 6-10 秒间隔。

#### OpenWeatherMap One Call 4.0（补充）

- 1.5 年扩展日预报（关键优势）
- 政府天气警报
- 免费层 1,000 调用/天
- 商用允许（ODbL + 署名）

## 地理编码 API

### 推荐：GeoNames（目的地数据）+ Nominatim（用户搜索）

#### GeoNames
- 1100 万+ 地名数据库
- 免费数据库导出
- CC BY 4.0
- 提供国家信息、时区、海拔

#### Nominatim (OpenStreetMap)
- 优质地址解析
- 1 请求/秒限制（公共 API）
- 生产环境需自托管或使用 LocationIQ

## API 成本估算

| 场景 | Amadeus 调用 | Open-Meteo 调用 | 预计成本 |
|---|---|---|---|
| 开发/测试（月） | ~5,000 | ~2,000 | $0 |
| 单次搜索（20 目的地） | ~20-40 | ~20 | ~$0.10 |
| 生产（1,000 搜索/月） | ~30,000 | ~20,000 | ~$80/月 |

## 不可直接获得的数据

1. **酒店精确价格** - Amadeus GDS 主要是连锁酒店，缺少 Airbnb/独立旅馆
2. **历史机票价格** - 需自行积累（Phase 6）
3. **景点营业时间** - 需 Google Places API 或手动数据
4. **公共交通路线** - 需 Google Directions API 或 GTFS 数据
5. **签证要求** - 国内旅行不需要，国际版需外部数据源

## 需要自行积累的数据

1. 航班价格快照（用于历史比较和价格提醒）
2. 酒店价格快照
3. 目的地详细标签和评分
4. 景点和活动数据
