from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.search import (
    ScoreBreakdown,
    ScoredDestination,
    SearchConstraints,
    SearchRequestSchema,
    SearchResponse,
)

logger = logging.getLogger(__name__)

PARSE_SYSTEM_PROMPT = """Extract travel search params from user description, return JSON only.

Fields: origin(IATA), preferred_departure_date(YYYY-MM-DD, default +30 days), date_flexibility_days(3), trip_length_min(3), trip_length_max(5), budget(USD, default 1500), preferences(tags), constraints({avoid_hot_weather:bool,avoid_cold_weather:bool,no_car_rental:bool,domestic_only:true})

Tags: beach,nature,food,city,museum,nightlife,relaxation,hiking,public_transport,family,budget,music,history,coffee,outdoor,skiing,architecture,art,shopping,entertainment,golf,quirky

IATA codes: ATL=亚特兰大,JFK/EWR=纽约,LAX=洛杉矶,SFO=旧金山,ORD=芝加哥,DFW=达拉斯,SEA=西雅图,BOS=波士顿,MIA=迈阿密,DEN=丹佛,MSP=明尼阿波利斯,PDX=波特兰,MSY=新奥尔良,BNA=纳什维尔,SAV=萨凡纳,CHS=查尔斯顿,SLC=盐湖城,PHX=凤凰城,HNL=檀香山,SAN=圣地亚哥,AUS=奥斯汀,CLT=夏洛特,TPA=坦帕,RDU=罗利,PIT=匹兹堡,STL=圣路易斯,KCI/MCI=堪萨斯城,CLE=克利夫兰,IND=印第安纳波利斯,CMH=哥伦布,ELP=厄尔巴索,ABQ=阿尔伯克基,OKC=俄克拉荷马城,TUL=塔尔萨,OMA=奥马哈,MEM=孟菲斯,JAX=杰克逊维尔,RIC=里士满,ORF=诺福克,BUF=布法罗,SYR=锡拉丘兹,HART=哈特福德,PVD=普罗维登斯,MHT=曼彻斯特

Return JSON only, no explanation."""

EXPLAIN_SYSTEM_PROMPT = """你是一个旅行推荐解释助手。根据搜索结果数据，用自然语言为用户解释为什么这些目的地被推荐，以及每个目的地的特点和适合程度。

要求：
- 用友好、自然的语气
- 每个目的地用 2-3 句话总结
- 突出每个目的地的独特优势
- 如果有预算或天气方面的注意事项，要提醒用户
- 用中文回复"""

ADVICE_SYSTEM_PROMPT = """你是一个旅行建议助手。根据目的地信息和用户偏好，提供详细的旅行建议。

要求：
- 推荐该目的地的必去景点和活动
- 建议最佳的出行方式和当地交通
- 提供饮食和住宿建议
- 提醒注意事项（天气、文化等）
- 用中文回复
- 控制在 300 字以内"""


class LLMService:
    def __init__(self):
        self._enabled = bool(settings.LLM_API_KEY and settings.LLM_BASE_URL)

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> str | None:
        if not self._enabled:
            return None

        api_type = settings.LLM_API_TYPE

        try:
            if api_type == "gemini":
                return await self._call_gemini(system_prompt, user_prompt, max_tokens, temperature, json_mode)
            else:
                return await self._call_openai_compat(system_prompt, user_prompt, max_tokens, temperature)
        except Exception as e:
            logger.warning(f"LLM call failed: {e}")
            return None

    async def _call_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> str | None:
        url = f"{settings.LLM_BASE_URL}/models/{settings.LLM_MODEL}:generateContent"

        body: dict[str, Any] = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

        if system_prompt:
            body["system_instruction"] = {"parts": [{"text": system_prompt}]}

        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"

        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            resp = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": settings.LLM_API_KEY,
                },
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return None

        return parts[0].get("text")

    async def _call_openai_compat(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str | None:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            resp = await client.post(
                f"{settings.LLM_BASE_URL}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.LLM_API_KEY}",
                },
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content

    @staticmethod
    def _extract_json(text: str) -> str | None:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]).strip()

        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

        return None

    async def parse_natural_language(self, text: str) -> SearchRequestSchema | None:
        if not self._enabled:
            return None

        api_type = settings.LLM_API_TYPE
        json_mode = api_type == "gemini"

        content = await self._call_llm(
            PARSE_SYSTEM_PROMPT, text, max_tokens=2000, temperature=0.1, json_mode=json_mode
        )
        if not content:
            return None

        try:
            content = content.strip()
            json_str = self._extract_json(content)
            if not json_str:
                json_str = content

            parsed = json.loads(json_str)

            dep_date = parsed.get("preferred_departure_date")
            if not dep_date:
                from datetime import date as date_type, timedelta
                today = date_type.today()
                dep_date = (today + timedelta(days=30)).isoformat()
                parsed["preferred_departure_date"] = dep_date

            constraints_data = parsed.get("constraints", {})
            constraints = SearchConstraints(
                max_flight_hours=constraints_data.get("max_flight_hours"),
                max_stops=constraints_data.get("max_stops"),
                avoid_hot_weather=constraints_data.get("avoid_hot_weather", False),
                avoid_cold_weather=constraints_data.get("avoid_cold_weather", False),
                no_car_rental=constraints_data.get("no_car_rental", False),
                domestic_only=constraints_data.get("domestic_only", True),
            )

            return SearchRequestSchema(
                origin=parsed.get("origin", "ATL"),
                preferred_departure_date=parsed.get("preferred_departure_date", dep_date),
                date_flexibility_days=parsed.get("date_flexibility_days", 3),
                trip_length_min=parsed.get("trip_length_min", 3),
                trip_length_max=parsed.get("trip_length_max", 5),
                budget=float(parsed.get("budget", 1500)),
                preferences=parsed.get("preferences", []),
                constraints=constraints,
            )
        except Exception as e:
            logger.warning(f"LLM parse failed: {e}")
            return None

    async def explain_results(self, response: SearchResponse, original_query: str | None = None) -> str:
        if not self._enabled:
            return ""

        results_text = ""
        for i, r in enumerate(response.top_results, 1):
            results_text += f"""
{i}. {r.city}, {r.state}
   - 出发: {r.departure_date} ~ 返程: {r.return_date} ({r.nights}晚)
   - 机票: ${r.flight_price:.0f} | 酒店: ${r.hotel_price:.0f} | 总计: ${r.estimated_total:.0f}
   - 天气: {r.weather_summary}
   - 总分: {r.total_score}/100
   - 评分: 机票{r.scores.flight} 酒店{r.scores.hotel} 天气{r.scores.weather} 偏好{r.scores.preference_match} 交通{r.scores.transport} 活动{r.scores.activities}
   - 优点: {', '.join(r.pros)}
   - 缺点: {', '.join(r.cons)}
   - 推荐理由: {r.recommendation_reason}
"""

        query_context = f"用户原始查询: {original_query}\n\n" if original_query else ""
        user_msg = f"{query_context}搜索结果:\n{results_text}\n请为用户总结这些推荐结果。"

        content = await self._call_llm(EXPLAIN_SYSTEM_PROMPT, user_msg, max_tokens=2000, temperature=0.7)
        return content or ""

    async def get_travel_advice(
        self,
        city: str,
        state: str,
        tags: list[str],
        climate_summary: str,
        budget_level: int,
        transport_score: int,
        user_preferences: list[str] | None = None,
    ) -> str:
        if not self._enabled:
            return ""

        user_msg = f"""请为以下目的地提供旅行建议：

城市: {city}, {state}
特色: {', '.join(tags)}
气候概况: {climate_summary}
消费等级: {budget_level}/5
公共交通评分: {transport_score}/10
{"用户偏好: " + ', '.join(user_preferences) if user_preferences else ""}"""

        content = await self._call_llm(ADVICE_SYSTEM_PROMPT, user_msg, max_tokens=1500, temperature=0.7)
        return content or ""


_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
