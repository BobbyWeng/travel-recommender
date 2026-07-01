from __future__ import annotations

import os
import tempfile
from datetime import date

import pytest

from app.core.db_cache import DBCacheService
from app.models.destination import Base
from app.schemas.search import (
    ScoreBreakdown,
    ScoredDestination,
    SearchConstraints,
    SearchRequestSchema,
    SearchResponse,
)
from app.services.search_history_service import SearchHistoryService
from sqlalchemy import create_engine


@pytest.fixture
def history_svc():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_url = f"sqlite:///{f.name}"
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    svc = SearchHistoryService(db_url=db_url)
    yield svc
    os.unlink(f.name)


def _make_response(request_id="test-123", origin="ATL") -> SearchResponse:
    return SearchResponse(
        request_id=request_id,
        origin=origin,
        top_results=[
            ScoredDestination(
                destination_id=1,
                city="New York",
                state="NY",
                iata_code="JFK",
                departure_date=date(2026, 9, 20),
                return_date=date(2026, 9, 25),
                nights=5,
                flight_price=300.0,
                hotel_price=800.0,
                estimated_total=1100.0,
                weather_summary="25°C/18°C",
                total_score=85.0,
                scores=ScoreBreakdown(
                    flight=80.0, hotel=70.0, weather=90.0,
                    preference_match=85.0, transport=80.0, activities=75.0,
                ),
                pros=["预算宽裕"],
                cons=[],
                recommendation_reason="满足偏好",
                data_source="mock",
            ),
        ],
        total_candidates_evaluated=20,
        total_candidates_filtered=15,
        data_source="mock",
    )


def _make_request(origin="ATL") -> SearchRequestSchema:
    return SearchRequestSchema(
        origin=origin,
        preferred_departure_date=date(2026, 9, 20),
        date_flexibility_days=3,
        trip_length_min=4,
        trip_length_max=5,
        budget=1500.0,
        preferences=["nature", "food"],
        constraints=SearchConstraints(),
    )


class TestSearchHistory:
    def test_save_and_list(self, history_svc):
        request = _make_request()
        response = _make_response()
        history_svc.save_search(request, response)

        searches = history_svc.list_searches()
        assert len(searches) == 1
        assert searches[0]["origin"] == "ATL"
        assert searches[0]["budget"] == 1500.0
        assert searches[0]["status"] == "completed"

    def test_get_search_detail(self, history_svc):
        request = _make_request()
        response = _make_response(request_id="detail-test")
        history_svc.save_search(request, response)

        detail = history_svc.get_search("detail-test")
        assert detail is not None
        assert detail["origin"] == "ATL"
        assert len(detail["results"]) == 1
        assert detail["results"][0]["total_score"] == 85.0
        assert detail["results"][0]["scores"]["flight"] == 80.0

    def test_get_nonexistent_search(self, history_svc):
        result = history_svc.get_search("nonexistent")
        assert result is None

    def test_multiple_searches_ordered(self, history_svc):
        for i in range(3):
            request = _make_request(origin=f"AT{i}")
            response = _make_response(request_id=f"search-{i}", origin=f"AT{i}")
            history_svc.save_search(request, response)

        searches = history_svc.list_searches()
        assert len(searches) == 3

    def test_search_count(self, history_svc):
        assert history_svc.get_search_count() == 0
        request = _make_request()
        response = _make_response()
        history_svc.save_search(request, response)
        assert history_svc.get_search_count() == 1

    def test_pagination(self, history_svc):
        for i in range(5):
            request = _make_request(origin=f"AT{i}")
            response = _make_response(request_id=f"page-{i}", origin=f"AT{i}")
            history_svc.save_search(request, response)

        page1 = history_svc.list_searches(limit=2, offset=0)
        assert len(page1) == 2
        page2 = history_svc.list_searches(limit=2, offset=2)
        assert len(page2) == 2
