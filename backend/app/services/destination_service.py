from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.schemas.search import SearchConstraints


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
