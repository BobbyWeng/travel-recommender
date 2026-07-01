from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.schemas.search import CandidatePreScore, SearchConstraints


@dataclass
class DestinationInfo:
    id: int
    city: str
    state: str
    country: str
    country_code: str
    iata_code: str
    latitude: float
    longitude: float
    timezone: str
    cost_level: int
    public_transport_score: int
    walkability_score: int
    tags: list[str]
    active: bool = True
    recommended_stay_days: int = 3
    destination_type: str = "city"
    gateway_airports: list[dict] | None = None
    requires_car: bool = False


@dataclass
class ClimateInfo:
    month: int
    temp_avg_c: float
    temp_max_avg_c: float
    temp_min_avg_c: float
    precip_days: float
    precip_mm: float
    sunshine_hours: float
    uv_index_avg: float
    wind_speed_avg_kmh: float


class DestinationService:
    def __init__(self, data_path: str | Path | None = None):
        self._destinations: list[DestinationInfo] = []
        self._climates: dict[int, list[ClimateInfo]] = {}
        if data_path:
            self.load_data(data_path)

    def load_data(self, data_path: str | Path) -> None:
        path = Path(data_path)
        if not path.exists():
            raise FileNotFoundError(f"目的地数据文件不存在: {path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        for idx, d in enumerate(data.get("destinations", []), start=1):
            dest = DestinationInfo(
                id=d.get("id", idx),
                city=d["city"],
                state=d["state"],
                country=d.get("country", "United States"),
                country_code=d.get("country_code", "US"),
                iata_code=d["iata_code"],
                latitude=d["latitude"],
                longitude=d["longitude"],
                timezone=d["timezone"],
                cost_level=d["cost_level"],
                public_transport_score=d["public_transport_score"],
                walkability_score=d.get("walkability_score", 5),
                tags=d.get("tags", []),
                recommended_stay_days=d.get("recommended_stay_days", 3),
                destination_type=d.get("destination_type", "city"),
                gateway_airports=d.get("gateway_airports"),
                requires_car=d.get("requires_car", False),
            )
            self._destinations.append(dest)

            climates = []
            for c in d.get("monthly_climate", []):
                climates.append(
                    ClimateInfo(
                        month=c["month"],
                        temp_avg_c=c["temp_avg_c"],
                        temp_max_avg_c=c["temp_max_avg_c"],
                        temp_min_avg_c=c["temp_min_avg_c"],
                        precip_days=c["precip_days"],
                        precip_mm=c["precip_mm"],
                        sunshine_hours=c["sunshine_hours"],
                        uv_index_avg=c["uv_index_avg"],
                        wind_speed_avg_kmh=c["wind_speed_avg_kmh"],
                    )
                )
            self._climates[dest.id] = climates

    def get_all_destinations(self) -> list[DestinationInfo]:
        return [d for d in self._destinations if d.active]

    def get_by_iata(self, iata: str) -> DestinationInfo | None:
        for d in self._destinations:
            if d.iata_code == iata and d.active:
                return d
        return None

    def get_by_id(self, dest_id: int) -> DestinationInfo | None:
        for d in self._destinations:
            if d.id == dest_id and d.active:
                return d
        return None

    def get_climate(self, dest_id: int, month: int) -> ClimateInfo | None:
        for c in self._climates.get(dest_id, []):
            if c.month == month:
                return c
        return None

    def filter_candidates(
        self,
        preferences: list[str],
        constraints: SearchConstraints,
        origin_iata: str | None = None,
    ) -> list[DestinationInfo]:
        candidates = self.get_all_destinations()

        if origin_iata:
            candidates = [d for d in candidates if d.iata_code != origin_iata]

        if constraints.domestic_only:
            candidates = [d for d in candidates if d.country_code == "US"]

        if constraints.no_car_rental:
            candidates = [d for d in candidates if d.public_transport_score >= 5]

        if preferences:
            scored = []
            for d in candidates:
                match_count = len(set(preferences) & set(d.tags))
                if match_count > 0:
                    scored.append((d, match_count))
            scored.sort(key=lambda x: x[1], reverse=True)
            candidates = [d for d, _ in scored]

        return candidates

    def pre_score_candidates(
        self,
        preferences: list[str],
        constraints: SearchConstraints,
        origin_iata: str | None = None,
        month: int | None = None,
        budget: float | None = None,
        max_candidates: int = 20,
    ) -> list[CandidatePreScore]:
        candidates = self.get_all_destinations()

        if origin_iata:
            candidates = [d for d in candidates if d.iata_code != origin_iata]

        if constraints.domestic_only:
            candidates = [d for d in candidates if d.country_code == "US"]

        if constraints.no_car_rental:
            candidates = [d for d in candidates if d.public_transport_score >= 5]

        origin_dest = self.get_by_iata(origin_iata) if origin_iata else None

        scored: list[CandidatePreScore] = []
        for d in candidates:
            climate_score = 0.0
            if month:
                climate = self.get_climate(d.id, month)
                if climate:
                    avg = climate.temp_avg_c
                    if 18 <= avg <= 28:
                        climate_score = 100.0
                    elif 10 <= avg < 18:
                        climate_score = 70.0 - (18 - avg) * 2
                    elif 28 < avg <= 35:
                        climate_score = 70.0 - (avg - 28) * 4
                    elif avg < 10:
                        climate_score = max(0, 40 - (10 - avg) * 3)
                    else:
                        climate_score = max(0, 30 - (avg - 35) * 5)
                    if climate.precip_days > 15:
                        climate_score -= 15
                    elif climate.precip_days > 10:
                        climate_score -= 5

            preference_score = 0.0
            if preferences:
                matched = len(set(preferences) & set(d.tags))
                preference_score = (matched / len(preferences)) * 100.0
            else:
                preference_score = 50.0

            transport_score = float(d.public_transport_score * 8 + d.walkability_score * 2)

            affordability_score = (6 - d.cost_level) * 20.0

            distance_score = 50.0
            if origin_dest:
                if origin_dest.state == d.state:
                    distance_score = 100.0
                elif self._same_region(origin_dest.state, d.state):
                    distance_score = 70.0
                else:
                    distance_score = 40.0

            total_score = (
                climate_score * 0.25
                + preference_score * 0.30
                + transport_score * 0.15
                + affordability_score * 0.15
                + distance_score * 0.15
            )

            scored.append(CandidatePreScore(
                destination_id=d.id,
                climate_score=round(climate_score, 1),
                preference_score=round(preference_score, 1),
                transport_score=round(transport_score, 1),
                affordability_score=round(affordability_score, 1),
                distance_score=round(distance_score, 1),
                total_score=round(total_score, 1),
            ))

        scored.sort(key=lambda s: s.total_score, reverse=True)
        return scored[:max_candidates]

    def filter_by_pre_score(
        self,
        preferences: list[str],
        constraints: SearchConstraints,
        origin_iata: str | None = None,
        month: int | None = None,
        budget: float | None = None,
        max_candidates: int = 20,
    ) -> list[DestinationInfo]:
        pre_scores = self.pre_score_candidates(
            preferences, constraints, origin_iata, month, budget, max_candidates
        )
        result = []
        for ps in pre_scores:
            dest = self.get_by_id(ps.destination_id)
            if dest:
                result.append(dest)
        return result

    @staticmethod
    def _same_region(state1: str, state2: str) -> bool:
        regions = {
            "Northeast": {"CT", "ME", "MA", "NH", "NJ", "NY", "PA", "RI", "VT"},
            "Southeast": {"AL", "AR", "DE", "FL", "GA", "KY", "LA", "MD", "MS", "NC", "SC", "TN", "VA", "WV", "DC"},
            "Midwest": {"IL", "IN", "IA", "KS", "MI", "MN", "MO", "NE", "ND", "OH", "SD", "WI"},
            "Southwest": {"AZ", "NM", "OK", "TX"},
            "West": {"AK", "CA", "CO", "HI", "ID", "MT", "NV", "OR", "UT", "WA", "WY"},
        }
        for region_states in regions.values():
            if state1 in region_states and state2 in region_states:
                return True
        return False
