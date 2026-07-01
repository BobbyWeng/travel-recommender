import random
from datetime import date

from app.core.config import settings
from app.providers.base import HotelProvider
from app.schemas.search import HotelResult, SourceMetadata, DataKind

_COST_LEVEL_NIGHTLY = {
    1: 80,
    2: 120,
    3: 180,
    4: 250,
    5: 350,
}

_DEST_COST_LEVELS: dict[str, int] = {}


def set_cost_levels(levels: dict[str, int]) -> None:
    _DEST_COST_LEVELS.update(levels)


class MockHotelProvider(HotelProvider):
    def __init__(self, seed: int | None = None):
        self._rng = random.Random((seed or settings.MOCK_SEED) + 1)

    async def search_hotels(
        self, city_iata: str, check_in: date, check_out: date, adults: int = 2
    ) -> HotelResult | None:
        nights = (check_out - check_in).days
        if nights <= 0:
            return None

        cost_level = _DEST_COST_LEVELS.get(city_iata, 3)
        base_nightly = _COST_LEVEL_NIGHTLY.get(cost_level, 180)

        season_factor = self._season_factor(check_in)
        nightly_price = base_nightly * season_factor
        nightly_price *= 1 + self._rng.uniform(-0.20, 0.20)
        nightly_price = round(nightly_price, 2)

        total_price = round(nightly_price * nights, 2)

        hotel_class = round(self._rng.uniform(2.5, 4.0), 1)
        areas = ["downtown", "midtown", "airport area", "waterfront", "old town"]
        area = self._rng.choice(areas)

        return HotelResult(
            destination_iata=city_iata,
            check_in=check_in,
            check_out=check_out,
            nightly_price=max(nightly_price, 60),
            total_price=total_price,
            currency="USD",
            hotel_class=hotel_class,
            area=area,
            source="mock",
            source_metadata=SourceMetadata(provider="mock", data_kind=DataKind.MOCK),
        )

    def _season_factor(self, d: date) -> float:
        month = d.month
        if month in (6, 7, 8, 12):
            return 1.20
        elif month in (1, 2, 9, 10):
            return 0.95
        else:
            return 1.05
