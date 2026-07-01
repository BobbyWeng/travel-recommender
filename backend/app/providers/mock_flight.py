import math
import random
from datetime import date, timedelta

from app.core.config import settings
from app.providers.base import FlightProvider
from app.schemas.search import FlightResult

_HUB_AIRPORTS = {
    "ATL", "DFW", "DEN", "ORD", "LAX", "CLT", "LAS", "PHX", "MIA",
    "SEA", "IAH", "JFK", "EWR", "SFO", "DTW", "MSP", "BOS", "SLC",
    "PHL", "BWI", "IAD", "DCA",
}

_COORDS: dict[str, tuple[float, float]] = {}


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_coords(iata: str) -> tuple[float, float]:
    if iata in _COORDS:
        return _COORDS[iata]
    return (33.75, -84.39)


def set_coordinates(coords: dict[str, tuple[float, float]]) -> None:
    _COORDS.update(coords)


class MockFlightProvider(FlightProvider):
    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed or settings.MOCK_SEED)

    async def search_flights(
        self, origin: str, destination: str, depart_date: date, return_date: date
    ) -> FlightResult | None:
        if origin == destination:
            return None

        lat1, lon1 = _get_coords(origin)
        lat2, lon2 = _get_coords(destination)
        miles = _haversine_miles(lat1, lon1, lat2, lon2)

        base_price = 0.12 * miles + 80
        season_factor = self._season_factor(depart_date)
        price = base_price * season_factor
        price *= 1 + self._rng.uniform(-0.15, 0.15)
        price = round(price, 2)

        flight_hours = miles / 500 + 0.5
        is_hub_origin = origin in _HUB_AIRPORTS
        is_hub_dest = destination in _HUB_AIRPORTS

        if is_hub_origin and is_hub_dest:
            stops = 0 if self._rng.random() < 0.7 else 1
        elif is_hub_origin or is_hub_dest:
            stops = 0 if self._rng.random() < 0.4 else 1
        else:
            stops = 0 if self._rng.random() < 0.2 else (1 if self._rng.random() < 0.7 else 2)

        total_duration_min = int(flight_hours * 60 + stops * 45)
        total_duration_min += self._rng.randint(-10, 30)

        airlines = ["Delta", "American", "United", "Southwest", "JetBlue", "Alaska"]
        airline = self._rng.choice(airlines)

        return FlightResult(
            origin=origin,
            destination=destination,
            departure_date=depart_date,
            return_date=return_date,
            price=max(price, 89),
            currency="USD",
            stops=stops,
            total_duration_min=max(total_duration_min, 60),
            airline=airline,
            source="mock",
        )

    async def search_cheapest_dates(
        self, origin: str, destination: str, start_date: date, end_date: date
    ) -> list[FlightResult]:
        results = []
        current = start_date
        while current <= end_date:
            result = await self.search_flights(origin, destination, current, current + timedelta(days=5))
            if result:
                results.append(result)
            current += timedelta(days=1)
        return results

    def _season_factor(self, d: date) -> float:
        month = d.month
        if month in (6, 7, 8, 12):
            return 1.25
        elif month in (1, 2, 9, 10):
            return 1.0
        else:
            return 0.85
