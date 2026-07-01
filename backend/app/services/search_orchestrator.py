from __future__ import annotations

import asyncio
import uuid
from datetime import date

from app.schemas.search import (
    FlightResult,
    HotelResult,
    ScoreBreakdown,
    ScoredDestination,
    SearchRequestSchema,
    SearchResponse,
    WeatherResult,
)
from app.services.date_search_service import generate_date_combinations
from app.services.destination_service import DestinationService
from app.services.flight_service import FlightService
from app.services.hotel_service import HotelService
from app.services.scoring_service import ScoringService
from app.services.weather_service import WeatherService


class SearchOrchestrator:
    def __init__(
        self,
        destination_service: DestinationService,
        flight_service: FlightService,
        hotel_service: HotelService,
        weather_service: WeatherService,
        scoring_service: ScoringService,
    ):
        self._dest_svc = destination_service
        self._flight_svc = flight_service
        self._hotel_svc = hotel_service
        self._weather_svc = weather_service
        self._scoring = scoring_service

    async def execute(self, request: SearchRequestSchema) -> SearchResponse:
        request_id = str(uuid.uuid4())
        warnings: list[str] = []

        date_combos = generate_date_combinations(
            preferred_date=request.preferred_departure_date,
            flexibility_days=request.date_flexibility_days,
            trip_length_min=request.trip_length_min,
            trip_length_max=request.trip_length_max,
        )

        if not date_combos:
            return SearchResponse(
                request_id=request_id, origin=request.origin,
                top_results=[], total_candidates_evaluated=0,
                total_candidates_filtered=0, data_source="none",
                warnings=["无法生成任何日期组合"],
            )

        candidates = self._dest_svc.filter_candidates(
            preferences=request.preferences,
            constraints=request.constraints,
            origin_iata=request.origin,
        )

        if not candidates:
            return SearchResponse(
                request_id=request_id, origin=request.origin,
                top_results=[], total_candidates_evaluated=0,
                total_candidates_filtered=0, data_source="none",
                warnings=["没有符合约束条件的候选目的地"],
            )

        scored_results: list[ScoredDestination] = []
        total_evaluated = 0
        total_filtered = 0
        data_sources: set[str] = set()

        for dest in candidates:
            best_for_dest: ScoredDestination | None = None

            sample_combos = self._select_sample_combos(date_combos)

            for combo in sample_combos:
                total_evaluated += 1

                flight, hotel, weather = await self._fetch_data_parallel(
                    request.origin, dest, combo
                )

                if flight:
                    data_sources.add(flight.source)
                if hotel:
                    data_sources.add(hotel.source)
                if weather and weather.days:
                    data_sources.add(weather.source)

                passed, constraint_warnings = self._scoring.check_hard_constraints(
                    flight=flight, hotel=hotel, weather=weather,
                    destination=dest, budget=request.budget,
                    constraints=request.constraints,
                )

                if not passed:
                    total_filtered += 1
                    continue

                if flight is None or hotel is None:
                    total_filtered += 1
                    continue

                scored = self._score_candidate(
                    dest, combo, flight, hotel, weather, request
                )

                if best_for_dest is None or scored.total_score > best_for_dest.total_score:
                    best_for_dest = scored

            if best_for_dest:
                scored_results.append(best_for_dest)

        scored_results.sort(key=lambda r: r.total_score, reverse=True)
        top_5 = scored_results[:5]

        source_str = "+".join(sorted(data_sources)) if data_sources else "none"

        return SearchResponse(
            request_id=request_id, origin=request.origin,
            top_results=top_5, total_candidates_evaluated=total_evaluated,
            total_candidates_filtered=total_filtered, data_source=source_str,
            warnings=warnings,
        )

    def _select_sample_combos(self, combos: list) -> list:
        if len(combos) <= 10:
            return combos

        step = len(combos) // 8
        sampled = []
        for i in range(0, len(combos), max(step, 1)):
            sampled.append(combos[i])
        if combos[-1] not in sampled:
            sampled.append(combos[-1])
        return sampled

    async def _fetch_data_parallel(
        self, origin: str, dest, combo
    ) -> tuple[FlightResult | None, HotelResult | None, WeatherResult | None]:
        flight_task = self._flight_svc.search(
            origin, dest.iata_code, combo.departure_date, combo.return_date
        )
        hotel_task = self._hotel_svc.search(
            dest.iata_code, combo.departure_date, combo.return_date
        )
        weather_task = self._weather_svc.get_forecast(
            dest.latitude, dest.longitude,
            combo.departure_date, combo.return_date,
            dest.iata_code,
        )

        results = await asyncio.gather(
            flight_task, hotel_task, weather_task,
            return_exceptions=True,
        )

        flight = results[0] if not isinstance(results[0], Exception) else None
        hotel = results[1] if not isinstance(results[1], Exception) else None
        weather = results[2] if not isinstance(results[2], Exception) else None

        return flight, hotel, weather

    def _score_candidate(
        self, dest, combo, flight, hotel, weather, request
    ) -> ScoredDestination:
        flight_score = self._scoring.score_flight(flight.price, request.budget)
        hotel_score = self._scoring.score_hotel(hotel.total_price, request.budget, flight.price)
        weather_score = self._scoring.score_weather(weather, request.constraints)
        pref_score = self._scoring.score_preference_match(dest, request.preferences)
        transport_score = self._scoring.score_transport(dest, request.constraints)
        activity_score = self._scoring.score_activities(dest, request.preferences)

        breakdown = ScoreBreakdown(
            flight=round(flight_score, 1),
            hotel=round(hotel_score, 1),
            weather=round(weather_score, 1),
            preference_match=round(pref_score, 1),
            transport=round(transport_score, 1),
            activities=round(activity_score, 1),
        )

        total_score = self._scoring.compute_total_score(breakdown)
        estimated_total = flight.price + hotel.total_price
        weather_summary = self._build_weather_summary(weather)

        pros, cons, reason = self._scoring.generate_pros_cons_reason(
            destination=dest, flight=flight, hotel=hotel,
            weather=weather, scores=breakdown,
            preferences=request.preferences, budget=request.budget,
        )

        sources = {flight.source, hotel.source}
        if weather and weather.days:
            sources.add(weather.source)

        return ScoredDestination(
            destination_id=dest.id, city=dest.city, state=dest.state,
            iata_code=dest.iata_code,
            departure_date=combo.departure_date, return_date=combo.return_date,
            nights=combo.nights,
            flight_price=flight.price, hotel_price=hotel.total_price,
            estimated_total=round(estimated_total, 2), currency="USD",
            weather_summary=weather_summary, total_score=total_score,
            scores=breakdown, pros=pros, cons=cons,
            recommendation_reason=reason,
            data_source="+".join(sorted(sources)),
        )

    def _build_weather_summary(self, weather) -> str:
        if not weather or not weather.days:
            return "暂无天气数据"
        avg_max = sum(d.temp_max_c for d in weather.days) / len(weather.days)
        avg_min = sum(d.temp_min_c for d in weather.days) / len(weather.days)
        avg_precip = sum(d.precip_probability for d in weather.days) / len(weather.days)
        return f"{avg_max:.0f}°C/{avg_min:.0f}°C, 降水概率 {avg_precip:.0f}%"
