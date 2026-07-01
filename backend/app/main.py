from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel as PydanticBaseModel
from app.core.config import settings

from app.core.config import settings
from app.core.database import init_db
from app.core.db_cache import get_db_cache
from app.providers.factory import create_flight_provider, create_hotel_provider, create_weather_provider
from app.schemas.search import (
    NaturalLanguageSearchRequest,
    NaturalLanguageSearchResponse,
    ScoreBreakdown,
    ScoredDestination,
    SearchConstraints,
    SearchRequestSchema,
    SearchResponse,
    TravelAdviceRequest,
    TravelAdviceResponse,
)
from app.services.destination_service import DestinationService
from app.services.flight_service import FlightService
from app.services.hotel_service import HotelService
from app.services.llm_service import get_llm_service
from app.services.scoring_service import ScoringService
from app.services.search_history_service import get_search_history
from app.services.search_orchestrator import SearchOrchestrator
from app.services.weather_service import WeatherService
from app.core.cache import flight_cache, hotel_cache, weather_cache

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

app = FastAPI(title="Travel Recommender API", version="0.5.0")

_cors_origins = [
    origin.strip()
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "")
        response = await call_next(request)
        if origin:
            allowed = origin in _cors_origins
            if not allowed:
                from urllib.parse import urlparse
                host = urlparse(origin).hostname or ""
                if host.endswith(".vercel.app"):
                    allowed = True
                elif host in ("localhost", "127.0.0.1"):
                    allowed = True
            if allowed:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                if "Access-Control-Allow-Methods" not in response.headers:
                    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
                if "Access-Control-Allow-Headers" not in response.headers:
                    response.headers["Access-Control-Allow-Headers"] = "*"
        return response


app.add_middleware(DynamicCORSMiddleware)

_search_store: dict[str, dict] = {}
_dest_svc: DestinationService | None = None
_orchestrator: SearchOrchestrator | None = None


def _get_data_path() -> str:
    return str(Path(__file__).parent.parent.parent / "data" / "destinations.json")


def _get_dest_svc() -> DestinationService:
    global _dest_svc
    if _dest_svc is None:
        _dest_svc = DestinationService(_get_data_path())
    return _dest_svc


def _get_orchestrator() -> SearchOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        dest_svc = _get_dest_svc()
        _orchestrator = SearchOrchestrator(
            destination_service=dest_svc,
            flight_service=FlightService(create_flight_provider(dest_svc)),
            hotel_service=HotelService(create_hotel_provider(dest_svc)),
            weather_service=WeatherService(create_weather_provider(dest_svc)),
            scoring_service=ScoringService(),
        )
    return _orchestrator


@app.on_event("startup")
async def startup():
    init_db()


@app.post("/search", response_model=SearchResponse)
async def create_search(request: SearchRequestSchema):
    orchestrator = _get_orchestrator()

    response = await orchestrator.execute(request)

    _search_store[response.request_id] = {
        "request": request.model_dump(mode="json"),
        "response": response.model_dump(mode="json"),
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        get_search_history().save_search(request, response)
    except Exception:
        pass

    return response


@app.post("/search/explain", response_model=SearchResponse)
async def create_search_with_explanation(request: SearchRequestSchema):
    orchestrator = _get_orchestrator()

    response = await orchestrator.execute(request)

    llm_svc = get_llm_service()
    if llm_svc.enabled:
        explanation = await llm_svc.explain_results(response)
        response.llm_explanation = explanation

    _search_store[response.request_id] = {
        "request": request.model_dump(mode="json"),
        "response": response.model_dump(mode="json"),
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        get_search_history().save_search(request, response)
    except Exception:
        pass

    return response


class ExplainRequest(PydanticBaseModel):
    search_id: str
    original_query: str = ""


@app.post("/explain")
async def explain_search_results(request: ExplainRequest):
    llm_svc = get_llm_service()
    if not llm_svc.enabled:
        return {"explanation": "LLM 服务未配置"}

    if request.search_id in _search_store:
        response_data = _search_store[request.search_id]["response"]
        response = SearchResponse(**response_data)
    else:
        db_search = get_search_history().get_search(request.search_id)
        if not db_search:
            raise HTTPException(status_code=404, detail="Search not found")
        response = _reconstruct_response(db_search)

    explanation = await llm_svc.explain_results(response, original_query=request.original_query)
    return {"explanation": explanation}


@app.post("/search/natural", response_model=NaturalLanguageSearchResponse)
async def natural_language_search(request: NaturalLanguageSearchRequest):
    llm_svc = get_llm_service()

    if not llm_svc.enabled:
        return NaturalLanguageSearchResponse(
            parse_error="LLM 服务未配置，请设置 LLM_API_KEY 和 LLM_BASE_URL"
        )

    import logging
    logger = logging.getLogger(__name__)
    logger.info("NL search: starting parse")
    
    parsed = await llm_svc.parse_natural_language(request.query)
    
    logger.info(f"NL search: parse done, result={parsed is not None}")
    
    if parsed is None:
        return NaturalLanguageSearchResponse(
            parse_error="无法理解您的搜索请求，请尝试更具体的描述"
        )

    logger.info("NL search: starting orchestrator")
    orchestrator = _get_orchestrator()

    response = await orchestrator.execute(parsed)
    
    logger.info(f"NL search: got {len(response.top_results)} results")

    _search_store[response.request_id] = {
        "request": parsed.model_dump(mode="json"),
        "response": response.model_dump(mode="json"),
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        get_search_history().save_search(parsed, response)
    except Exception:
        pass

    return NaturalLanguageSearchResponse(
        parsed_request=parsed,
        search_response=response,
        llm_explanation="",
    )


@app.post("/destinations/{dest_id}/advice", response_model=TravelAdviceResponse)
async def get_travel_advice(dest_id: int, request: TravelAdviceRequest):
    dest_svc = _get_dest_svc()
    d = dest_svc.get_by_id(dest_id)
    if not d:
        raise HTTPException(status_code=404, detail="Destination not found")

    llm_svc = get_llm_service()
    if not llm_svc.enabled:
        return TravelAdviceResponse(
            destination_id=dest_id,
            city=d.city,
            state=d.state,
            advice="LLM 服务未配置",
        )

    climate = dest_svc.get_climate(d.id, 9)
    climate_summary = ""
    if climate:
        climate_summary = f"9月平均最高温 {climate.temp_max_avg_c}°C，最低温 {climate.temp_min_avg_c}°C，降水 {climate.precip_days} 天"

    advice = await llm_svc.get_travel_advice(
        city=d.city,
        state=d.state,
        tags=d.tags,
        climate_summary=climate_summary,
        budget_level=d.cost_level,
        transport_score=d.public_transport_score,
        user_preferences=request.preferences,
    )

    return TravelAdviceResponse(
        destination_id=dest_id,
        city=d.city,
        state=d.state,
        advice=advice,
    )


@app.get("/search/{search_id}", response_model=SearchResponse)
async def get_search(search_id: str):
    if search_id not in _search_store:
        db_search = get_search_history().get_search(search_id)
        if db_search:
            return _reconstruct_response(db_search)
        raise HTTPException(status_code=404, detail="Search not found")
    return _search_store[search_id]["response"]


@app.get("/searches")
async def list_searches(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return get_search_history().list_searches(limit=limit, offset=offset)


@app.get("/searches/{search_id}")
async def get_search_detail(search_id: str):
    result = get_search_history().get_search(search_id)
    if not result:
        raise HTTPException(status_code=404, detail="Search not found")
    return result


@app.get("/destinations")
async def list_destinations(
    tags: str | None = None,
    min_transit: int | None = None,
):
    dest_svc = _get_dest_svc()
    destinations = dest_svc.get_all_destinations()

    if tags:
        tag_set = set(tags.split(","))
        destinations = [d for d in destinations if tag_set & set(d.tags)]

    if min_transit is not None:
        destinations = [d for d in destinations if d.public_transport_score >= min_transit]

    return [
        {
            "id": d.id,
            "city": d.city,
            "state": d.state,
            "iata_code": d.iata_code,
            "latitude": d.latitude,
            "longitude": d.longitude,
            "cost_level": d.cost_level,
            "public_transport_score": d.public_transport_score,
            "walkability_score": d.walkability_score,
            "tags": d.tags,
        }
        for d in destinations
    ]


@app.get("/destinations/{dest_id}")
async def get_destination(dest_id: int):
    dest_svc = _get_dest_svc()
    d = dest_svc.get_by_id(dest_id)
    if not d:
        raise HTTPException(status_code=404, detail="Destination not found")

    climates = []
    for month in range(1, 13):
        c = dest_svc.get_climate(d.id, month)
        if c:
            climates.append({
                "month": c.month,
                "temp_max_avg_c": c.temp_max_avg_c,
                "temp_min_avg_c": c.temp_min_avg_c,
                "precip_days": c.precip_days,
                "precip_mm": c.precip_mm,
                "sunshine_hours": c.sunshine_hours,
                "uv_index_avg": c.uv_index_avg,
            })

    return {
        "id": d.id,
        "city": d.city,
        "state": d.state,
        "country": d.country,
        "iata_code": d.iata_code,
        "latitude": d.latitude,
        "longitude": d.longitude,
        "timezone": d.timezone,
        "cost_level": d.cost_level,
        "public_transport_score": d.public_transport_score,
        "walkability_score": d.walkability_score,
        "tags": d.tags,
        "monthly_climate": climates,
    }


@app.get("/health")
async def health():
    amadeus_configured = bool(settings.AMADEUS_CLIENT_ID and settings.AMADEUS_CLIENT_SECRET)
    duffel_configured = bool(settings.DUFFEL_ENABLED and settings.DUFFEL_ACCESS_TOKEN)
    llm_svc = get_llm_service()
    cache_stats = get_db_cache().get_cache_stats()

    if duffel_configured:
        flight_provider = "duffel"
    elif amadeus_configured:
        flight_provider = "amadeus"
    elif settings.APP_ENV == "production" and not settings.ALLOW_MOCK_FALLBACK:
        flight_provider = "not_configured"
    else:
        flight_provider = "mock"

    hotel_provider = "amadeus" if amadeus_configured else ("mock" if settings.ALLOW_MOCK_FALLBACK else "not_configured")

    return {
        "status": "ok",
        "version": "0.5.0",
        "environment": settings.APP_ENV,
        "providers": {
            "flight": flight_provider,
            "hotel": hotel_provider,
            "weather": "open-meteo",
        },
        "duffel_configured": duffel_configured,
        "llm": {
            "enabled": llm_svc.enabled,
            "model": settings.LLM_MODEL if llm_svc.enabled else None,
        },
        "destinations_count": len(_get_dest_svc().get_all_destinations()),
        "cache": cache_stats,
        "memory_cache": {
            "flight": flight_cache.get_stats().__dict__,
            "hotel": hotel_cache.get_stats().__dict__,
            "weather": weather_cache.get_stats().__dict__,
        },
    }


@app.post("/cache/cleanup")
async def cleanup_cache():
    counts = get_db_cache().cleanup_expired()
    return {"cleaned": counts}


def _reconstruct_response(db_search: dict) -> SearchResponse:
    from app.schemas.search import ScoreBreakdown

    top_results = []
    for r in db_search.get("results", []):
        scores = r.get("scores", {})
        top_results.append(
            ScoredDestination(
                destination_id=r["destination_id"],
                city="",
                state="",
                iata_code="",
                departure_date=date.fromisoformat(r["departure_date"]),
                return_date=date.fromisoformat(r["return_date"]),
                nights=0,
                flight_price=r.get("flight_price", 0),
                hotel_price=r.get("hotel_price", 0),
                estimated_total=r.get("estimated_total", 0),
                weather_summary="",
                total_score=r.get("total_score", 0),
                scores=ScoreBreakdown(**scores) if scores else ScoreBreakdown(),
                pros=[],
                cons=[],
                recommendation_reason=r.get("recommendation_reason", ""),
                data_source="cached",
            )
        )

    return SearchResponse(
        request_id=db_search["id"],
        origin=db_search["origin"],
        top_results=top_results,
        total_candidates_evaluated=0,
        total_candidates_filtered=0,
        data_source="cached",
    )
