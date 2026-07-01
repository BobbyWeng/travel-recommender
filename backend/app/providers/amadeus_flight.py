from __future__ import annotations

from datetime import date, timedelta

import httpx

from app.providers.amadeus_auth import AmadeusAuthClient
from app.providers.base import FlightProvider
from app.schemas.search import FlightResult, SourceMetadata, DataKind


class AmadeusFlightProvider(FlightProvider):
    def __init__(self):
        self._auth = AmadeusAuthClient.get_instance()
        self._env = self._auth._env
        self._base_url = self._auth._base_url

    async def search_flights(
        self, origin: str, destination: str, depart_date: date, return_date: date
    ) -> FlightResult | None:
        try:
            token = await self._auth.get_access_token()
        except Exception:
            return None

        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": depart_date.isoformat(),
            "returnDate": return_date.isoformat(),
            "adults": 1,
            "currencyCode": "USD",
            "max": 5,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self._base_url}/v2/shopping/flight-offers",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 429:
                    return None
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, httpx.TimeoutException):
            return None

        offers = data.get("data", [])
        if not offers:
            return None

        offer = offers[0]
        price = float(offer.get("price", {}).get("total", 0))

        itineraries = offer.get("itineraries", [])
        total_duration_min = 0
        max_stops = 0
        airlines = set()

        for itin in itineraries:
            duration_str = itin.get("duration", "PT0H0M")
            total_duration_min += self._parse_duration(duration_str)
            for seg in itin.get("segments", []):
                max_stops = max(max_stops, len(itin.get("segments", [])) - 1)
                carrier = seg.get("carrierCode", "")
                if carrier:
                    airlines.add(carrier)

        return FlightResult(
            origin=origin,
            destination=destination,
            departure_date=depart_date,
            return_date=return_date,
            price=round(price, 2),
            currency="USD",
            stops=max_stops,
            total_duration_min=total_duration_min,
            airline=", ".join(sorted(airlines)) if airlines else None,
            source="amadeus",
            source_metadata=SourceMetadata(provider="amadeus", data_kind=DataKind.LIVE),
        )

    async def search_cheapest_dates(
        self, origin: str, destination: str, start_date: date, end_date: date
    ) -> list[FlightResult]:
        try:
            token = await self._auth.get_access_token()
        except Exception:
            return []

        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": start_date.isoformat(),
            "returnDate": (start_date + timedelta(days=5)).isoformat(),
            "currencyCode": "USD",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self._base_url}/v1/shopping/flight-dates",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code in (429, 404):
                    return []
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, httpx.TimeoutException):
            return []

        results = []
        for flight_date in data.get("data", []):
            price = float(flight_date.get("price", {}).get("total", 0))
            dep_date_str = flight_date.get("departureDate", "")
            ret_date_str = flight_date.get("returnDate", "")
            if dep_date_str and price > 0:
                try:
                    dep = date.fromisoformat(dep_date_str)
                    ret = date.fromisoformat(ret_date_str) if ret_date_str else dep + timedelta(days=5)
                    results.append(
                        FlightResult(
                            origin=origin,
                            destination=destination,
                            departure_date=dep,
                            return_date=ret,
                            price=round(price, 2),
                            source="amadeus",
                            stops=0,
                            total_duration_min=0,
                            source_metadata=SourceMetadata(provider="amadeus", data_kind=DataKind.LIVE),
                        )
                    )
                except ValueError:
                    continue
        return results

    @staticmethod
    def _parse_duration(duration: str) -> int:
        minutes = 0
        import re

        hours = re.search(r"(\d+)H", duration)
        mins = re.search(r"(\d+)M", duration)
        if hours:
            minutes += int(hours.group(1)) * 60
        if mins:
            minutes += int(mins.group(1))
        return minutes
