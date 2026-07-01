from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.destination import SearchCandidate, SearchRequest as SearchRequestModel
from app.schemas.search import ScoredDestination, SearchRequestSchema, SearchResponse


class SearchHistoryService:
    def __init__(self, db_url: str | None = None):
        self._engine = create_engine(db_url or settings.DATABASE_URL, echo=False)

    def save_search(
        self,
        request_schema: SearchRequestSchema,
        response: SearchResponse,
    ) -> None:
        now = datetime.utcnow()
        with Session(self._engine) as session:
            db_req = SearchRequestModel(
                id=response.request_id,
                origin=request_schema.origin,
                preferred_departure_date=request_schema.preferred_departure_date,
                date_flexibility_days=request_schema.date_flexibility_days,
                trip_length_min=request_schema.trip_length_min,
                trip_length_max=request_schema.trip_length_max,
                budget=request_schema.budget,
                currency=request_schema.currency,
                preferences=json.dumps(request_schema.preferences),
                constraints=request_schema.constraints.model_dump_json(),
                status="completed",
                created_at=now,
                completed_at=now,
            )
            session.add(db_req)

            for result in response.top_results:
                candidate = SearchCandidate(
                    search_id=response.request_id,
                    destination_id=result.destination_id,
                    departure_date=result.departure_date,
                    return_date=result.return_date,
                    flight_price=result.flight_price,
                    hotel_price=result.hotel_price,
                    estimated_total=result.estimated_total,
                    flight_score=result.scores.flight,
                    hotel_score=result.scores.hotel,
                    weather_score=result.scores.weather,
                    preference_score=result.scores.preference_match,
                    transport_score=result.scores.transport,
                    activity_score=result.scores.activities,
                    total_score=result.total_score,
                    passed_constraints=True,
                    recommendation_reason=result.recommendation_reason,
                )
                session.add(candidate)

            session.commit()

    def list_searches(self, limit: int = 20, offset: int = 0) -> list[dict]:
        with Session(self._engine) as session:
            rows = (
                session.query(SearchRequestModel)
                .order_by(desc(SearchRequestModel.created_at))
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "origin": r.origin,
                    "preferred_departure_date": r.preferred_departure_date.isoformat(),
                    "budget": r.budget,
                    "preferences": json.loads(r.preferences) if r.preferences else [],
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]

    def get_search(self, search_id: str) -> dict | None:
        with Session(self._engine) as session:
            req = session.query(SearchRequestModel).filter_by(id=search_id).first()
            if not req:
                return None

            candidates = (
                session.query(SearchCandidate)
                .filter_by(search_id=search_id)
                .order_by(desc(SearchCandidate.total_score))
                .all()
            )

            return {
                "id": req.id,
                "origin": req.origin,
                "preferred_departure_date": req.preferred_departure_date.isoformat(),
                "date_flexibility_days": req.date_flexibility_days,
                "trip_length_min": req.trip_length_min,
                "trip_length_max": req.trip_length_max,
                "budget": req.budget,
                "currency": req.currency,
                "preferences": json.loads(req.preferences) if req.preferences else [],
                "constraints": json.loads(req.constraints) if req.constraints else {},
                "status": req.status,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "completed_at": req.completed_at.isoformat() if req.completed_at else None,
                "results": [
                    {
                        "destination_id": c.destination_id,
                        "departure_date": c.departure_date.isoformat(),
                        "return_date": c.return_date.isoformat(),
                        "flight_price": c.flight_price,
                        "hotel_price": c.hotel_price,
                        "estimated_total": c.estimated_total,
                        "total_score": c.total_score,
                        "recommendation_reason": c.recommendation_reason,
                        "scores": {
                            "flight": c.flight_score,
                            "hotel": c.hotel_score,
                            "weather": c.weather_score,
                            "preference_match": c.preference_score,
                            "transport": c.transport_score,
                            "activities": c.activity_score,
                        },
                    }
                    for c in candidates
                ],
            }

    def get_search_count(self) -> int:
        with Session(self._engine) as session:
            return session.query(SearchRequestModel).count()


_search_history: SearchHistoryService | None = None


def get_search_history() -> SearchHistoryService:
    global _search_history
    if _search_history is None:
        _search_history = SearchHistoryService()
    return _search_history
