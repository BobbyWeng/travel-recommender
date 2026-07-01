from __future__ import annotations

import asyncio
import time
import uuid
from datetime import date, timedelta

from app.schemas.search import (
    CandidatePreScore,
    DataKind,
    DataQualitySummary,
    FlightResult,
    HotelResult,
    ScoreBreakdown,
    ScoredDestination,
    SearchExecutionBudget,
    SearchExecutionStats,
    SearchRequestSchema,
    SearchResponse,
    SourceMetadata,
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
        budget: SearchExecutionBudget | None = None,
    ):
        self._dest_svc = destination_service
        self._flight_svc = flight_service
        self._hotel_svc = hotel_service
        self._weather_svc = weather_service
        self._scoring = scoring_service
        self._budget = budget or SearchExecutionBudget()

    async def execute(self, request: SearchRequestSchema) -> SearchResponse:
        start_time = time.monotonic()
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

        provider_calls = 0
        cache_hits = 0
        provider_failures = 0
        fallback_count = 0
        budget_exhausted = False

        month = request.preferred_departure_date.month

        stage1_scores = self._dest_svc.pre_score_candidates(
            preferences=request.preferences,
            constraints=request.constraints,
            origin_iata=request.origin,
            month=month,
            budget=request.budget,
            max_candidates=self._budget.max_stage1_candidates,
        )
        stage1_ids = [s.destination_id for s in stage1_scores]
        stage1_dests = []
        for did in stage1_ids:
            d = self._dest_svc.get_by_id(did)
            if d:
                stage1_dests.append(d)

        if not stage1_dests:
            return SearchResponse(
                request_id=request_id, origin=request.origin,
                top_results=[], total_candidates_evaluated=0,
                total_candidates_filtered=0, data_source="none",
                warnings=["没有符合约束条件的候选目的地"],
            )

        semaphore = asyncio.Semaphore(self._budget.max_concurrency)

        stage2_results: list[tuple[DestinationInfo, ScoredDestination]] = []
        total_evaluated = 0
        total_filtered = 0
        data_sources: set[str] = set()

        async def _process_stage2_combo(dest, combo):
            nonlocal provider_calls, cache_hits, fallback_count, budget_exhausted

            if provider_calls >= self._budget.max_provider_calls:
                budget_exhausted = True
                return None

            async with semaphore:
                if provider_calls >= self._budget.max_provider_calls:
                    budget_exhausted = True
                    return None

                flight, hotel, weather = await self._fetch_data_parallel(
                    request.origin, dest, combo
                )

                provider_calls += 3

                if flight:
                    data_sources.add(flight.source)
                    if flight.source_metadata:
                        if flight.source_metadata.cache_hit:
                            cache_hits += 1
                        if flight.source_metadata.fallback_used:
                            fallback_count += 1
                if hotel:
                    data_sources.add(hotel.source)
                    if hotel.source_metadata:
                        if hotel.source_metadata.cache_hit:
                            cache_hits += 1
                        if hotel.source_metadata.fallback_used:
                            fallback_count += 1
                if weather and weather.days:
                    data_sources.add(weather.source)
                    if weather.source_metadata:
                        if weather.source_metadata.fallback_used:
                            fallback_count += 1

                passed, _ = self._scoring.check_hard_constraints(
                    flight=flight, hotel=hotel, weather=weather,
                    destination=dest, budget=request.budget,
                    constraints=request.constraints,
                )

                if not passed or flight is None or hotel is None:
                    return None

                scored = self._score_candidate(
                    dest, combo, flight, hotel, weather, request
                )
                return scored

        for dest in stage1_dests:
            if budget_exhausted:
                break

            rep_combos = self._select_representative_dates(
                date_combos, request.preferred_departure_date,
                request.date_flexibility_days,
                self._budget.max_stage2_date_samples,
            )

            best_for_dest: ScoredDestination | None = None
            for combo in rep_combos:
                if budget_exhausted:
                    break
                total_evaluated += 1
                result = await _process_stage2_combo(dest, combo)
                if result is None:
                    total_filtered += 1
                    continue
                if best_for_dest is None or result.total_score > best_for_dest.total_score:
                    best_for_dest = result

            if best_for_dest:
                stage2_results.append((dest, best_for_dest))

            if len(stage2_results) >= self._budget.max_stage2_candidates:
                break

        stage2_results.sort(key=lambda x: x[1].total_score, reverse=True)
        stage2_top = stage2_results[:self._budget.max_stage2_candidates]

        stage3_results: list[ScoredDestination] = []

        for dest, stage2_best in stage2_top:
            if budget_exhausted:
                stage3_results.append(stage2_best)
                continue

            remaining_combos = [c for c in date_combos if c not in self._select_representative_dates(
                date_combos, request.preferred_departure_date,
                request.date_flexibility_days,
                self._budget.max_stage2_date_samples,
            )]

            sampled_remaining = self._select_sample_combos(remaining_combos)
            best_for_dest = stage2_best

            for combo in sampled_remaining:
                if budget_exhausted:
                    break
                total_evaluated += 1
                result = await _process_stage2_combo(dest, combo)
                if result is None:
                    total_filtered += 1
                    continue
                if result.total_score > best_for_dest.total_score:
                    best_for_dest = result

            stage3_results.append(best_for_dest)

        stage3_results.sort(key=lambda r: r.total_score, reverse=True)
        top_5 = stage3_results[:5]

        source_str = "+".join(sorted(data_sources)) if data_sources else "none"
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        return SearchResponse(
            request_id=request_id, origin=request.origin,
            top_results=top_5, total_candidates_evaluated=total_evaluated,
            total_candidates_filtered=total_filtered, data_source=source_str,
            warnings=warnings,
            execution_stats=SearchExecutionStats(
                stage1_candidates=len(stage1_dests),
                stage2_candidates=len(stage2_results),
                stage3_candidates=len(stage3_results),
                provider_calls=provider_calls,
                cache_hits=cache_hits,
                provider_failures=provider_failures,
                fallback_count=fallback_count,
                elapsed_ms=elapsed_ms,
                budget_exhausted=budget_exhausted,
            ),
        )

    def _select_representative_dates(
        self,
        combos: list,
        preferred_date: date,
        flexibility_days: int,
        max_samples: int = 5,
    ) -> list:
        if not combos:
            return []

        seen_dates: set[date] = set()
        selected: list = []

        preferred_combos = [c for c in combos if c.departure_date == preferred_date]
        for c in preferred_combos:
            if c not in selected:
                selected.append(c)
                seen_dates.add(c.departure_date)

        earliest = preferred_date - timedelta(days=flexibility_days)
        earliest_combos = [c for c in combos if c.departure_date == earliest and c not in selected]
        if earliest_combos:
            selected.append(earliest_combos[0])
            seen_dates.add(earliest)

        latest = preferred_date + timedelta(days=flexibility_days)
        latest_combos = [c for c in combos if c.departure_date == latest and c not in selected]
        if latest_combos:
            selected.append(latest_combos[0])
            seen_dates.add(latest)

        weekday_date = None
        for delta in range(-3, 4):
            d = preferred_date + timedelta(days=delta)
            if d.weekday() < 5 and d not in seen_dates:
                weekday_date = d
                break
        if weekday_date:
            weekday_combos = [c for c in combos if c.departure_date == weekday_date and c not in selected]
            if weekday_combos:
                selected.append(weekday_combos[0])
                seen_dates.add(weekday_date)

        weekend_date = None
        for delta in range(-3, 4):
            d = preferred_date + timedelta(days=delta)
            if d.weekday() >= 5 and d not in seen_dates:
                weekend_date = d
                break
        if weekend_date:
            weekend_combos = [c for c in combos if c.departure_date == weekend_date and c not in selected]
            if weekend_combos:
                selected.append(weekend_combos[0])
                seen_dates.add(weekend_date)

        if len(selected) < max_samples:
            step = max(1, len(combos) // (max_samples - len(selected) + 1))
            for i in range(0, len(combos), step):
                if combos[i] not in selected:
                    selected.append(combos[i])
                if len(selected) >= max_samples:
                    break

        return selected[:max_samples]

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

        flight_data_kind = None
        hotel_data_kind = None
        weather_data_kind = None

        if flight.source_metadata:
            flight_data_kind = flight.source_metadata.data_kind
        if hotel.source_metadata:
            hotel_data_kind = hotel.source_metadata.data_kind
        if weather and weather.source_metadata:
            weather_data_kind = weather.source_metadata.data_kind

        data_quality = self._compute_data_quality(flight, hotel, weather)

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
            flight_data_kind=flight_data_kind,
            hotel_data_kind=hotel_data_kind,
            weather_data_kind=weather_data_kind,
            data_quality=data_quality,
        )

    def _compute_data_quality(
        self, flight: FlightResult | None, hotel: HotelResult | None, weather: WeatherResult | None
    ) -> DataQualitySummary:
        live_count = 0
        cached_count = 0
        historical_count = 0
        estimated_count = 0
        mock_count = 0
        unavailable_count = 0
        available_fields = 0

        for result in [flight, hotel]:
            if result and result.source_metadata:
                kind = result.source_metadata.data_kind
                available_fields += 1
                if kind == DataKind.LIVE:
                    live_count += 1
                elif kind == DataKind.CACHED:
                    cached_count += 1
                elif kind == DataKind.HISTORICAL:
                    historical_count += 1
                elif kind == DataKind.ESTIMATED:
                    estimated_count += 1
                elif kind == DataKind.MOCK:
                    mock_count += 1
                elif kind == DataKind.UNAVAILABLE:
                    unavailable_count += 1
            elif result:
                available_fields += 1
            else:
                unavailable_count += 1

        if weather and weather.source_metadata:
            available_fields += 1
            kind = weather.source_metadata.data_kind
            if kind == DataKind.LIVE:
                live_count += 1
            elif kind == DataKind.CACHED:
                cached_count += 1
            elif kind == DataKind.HISTORICAL:
                historical_count += 1
            elif kind == DataKind.ESTIMATED:
                estimated_count += 1
            elif kind == DataKind.MOCK:
                mock_count += 1
            elif kind == DataKind.UNAVAILABLE:
                unavailable_count += 1
        elif weather and weather.days:
            available_fields += 1
        else:
            unavailable_count += 1

        completeness = available_fields / 3.0 if available_fields > 0 else 0.0

        return DataQualitySummary(
            completeness=round(completeness, 2),
            live_field_count=live_count,
            cached_field_count=cached_count,
            historical_field_count=historical_count,
            estimated_field_count=estimated_count,
            mock_field_count=mock_count,
            unavailable_field_count=unavailable_count,
        )

    def _build_weather_summary(self, weather) -> str:
        if not weather or not weather.days:
            return "暂无天气数据"
        avg_max = sum(d.temp_max_c for d in weather.days) / len(weather.days)
        avg_min = sum(d.temp_min_c for d in weather.days) / len(weather.days)
        avg_precip = sum(d.precip_probability for d in weather.days) / len(weather.days)
        return f"{avg_max:.0f}°C/{avg_min:.0f}°C, 降水概率 {avg_precip:.0f}%"
