# 部署指南

## GitHub 仓库

```
https://github.com/BobbyWeng/travel-recommender
```

分支: `main`

## 本地运行

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查: `curl http://localhost:8000/health`

### 前端

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

访问: http://localhost:3000

## Render 后端部署

### 配置

| 项目 | 值 |
|------|-----|
| Service Type | Web Service |
| Repository | travel-recommender |
| Branch | main |
| Root Directory | backend |
| Runtime | Python |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

### 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `APP_ENV` | `production` | ✅ |
| `ALLOW_MOCK_FALLBACK` | `false` | ✅ |
| `CORS_ORIGINS` | 逗号分隔的前端域名 | ✅ |
| `DATABASE_URL` | SQLite 路径或 PostgreSQL URL | ✅ |
| `OPEN_METEO_BASE_URL` | `https://archive-api.open-meteo.com` | ❌ |
| `LLM_API_KEY` | LLM API Key | ❌ |
| `LLM_BASE_URL` | LLM API Base URL | ❌ |
| `LLM_MODEL` | 模型名称 | ❌ |
| `LLM_API_TYPE` | `gemini` 或 `openai` | ❌ |
| `AMADEUS_CLIENT_ID` | Amadeus API ID | ❌ |
| `AMADEUS_CLIENT_SECRET` | Amadeus API Secret | ❌ |
| `DUFFEL_ACCESS_TOKEN` | Duffel API Token | ❌ |
| `DUFFEL_ENABLED` | `true`/`false` | ❌ |
| `FLIGHT_PROVIDER` | `auto`/`duffel`/`amadeus`/`mock` | ❌ |

## Vercel 前端部署

### 配置

| 项目 | 值 |
|------|-----|
| Framework Preset | Next.js |
| Root Directory | frontend |
| Build Command | `npm run build` |
| Install Command | `npm ci` |

### 环境变量

| 变量 | 说明 |
|------|------|
| `NEXT_PUBLIC_API_BASE_URL` | Render 后端地址 (如 `https://xxx.onrender.com`) |

**不要**在前端配置任何后端私密 Key。

## CORS 配置

后端 `CORS_ORIGINS` 必须包含实际前端域名。

示例:
```
CORS_ORIGINS=http://localhost:3000,https://travel-recommender.vercel.app
```

更新 CORS 后需重新部署 Render。

## 数据库

### SQLite（临时部署）

当前默认使用 SQLite。Render 文件系统为临时存储，重新部署后搜索历史和缓存可能丢失。

DATABASE_URL 示例:
```
DATABASE_URL=sqlite:///./data/travel.db
```

### PostgreSQL（生产推荐）

在 Render 创建 PostgreSQL 数据库后，将内部连接字符串配置为 `DATABASE_URL`。

项目使用 SQLAlchemy，理论上支持 PostgreSQL，但需确认所有 SQL 语法兼容。迁移前建议本地测试。

## Mock/Demo 模式

### 生产模式（推荐）

```
APP_ENV=production
ALLOW_MOCK_FALLBACK=false
```

- 没有真实 Provider 时不返回模拟数据
- 前端显示"实时价格服务尚未配置"
- 搜索结果不会把 Mock 当真实数据

### 演示模式

```
APP_ENV=demo
ALLOW_MOCK_FALLBACK=true
```

- 前端必须显示"演示数据，不代表真实可预订价格"
- 仅用于功能展示

## 临时域名说明

当前使用平台临时域名:
- Render: `https://xxx.onrender.com`
- Vercel: `https://xxx.vercel.app`

尚未绑定自定义域名。

## 关闭 Demo/Mock 模式

1. 在 Render 设置 `ALLOW_MOCK_FALLBACK=false`
2. 配置至少一个真实航班 Provider（Amadeus 或 Duffel）
3. 重新部署
