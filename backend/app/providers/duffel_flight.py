from __future__ import annotations

import asyncio
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx

from app.core.config import settings
from app.providers.base import FlightProvider
from app.providers.errors import ProviderError, ProviderErrorCode
from app.schemas.search import (
    DataKind,
    FlightOffer,
    FlightResult,
    FlightSegment,
    FlightSlice,
    SourceMetadata,
)


class DuffelFlightProvider(FlightProvider):
    def __init__(self):
        self._base_url = settings.DUFFEL_BASE_URL
        self._token = settings.DUFFEL_ACCESS_TOKEN
        self._timeout = settings.DUFFEL_TIMEOUT_SECONDS
        self._max_retries = settings.DUFFEL_MAX_RETRIES

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Duffel-Version": "v2",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def search_flights(
        self, origin: str, destination: str, depart_date: date, return_date: date
    ) -> FlightResult | None:
        payload = {
            "data": {
                "slices": [
                    {
                        "origin": origin,
                        "destination": destination,
                        "departure_date": depart_date.isoformat(),
                    },
                    {
                        "origin": destination,
                        "destination": origin,
                        "departure_date": return_date.isoformat(),
                    },
                ],
                "passengers": [{"type": "adult"}],
                "cabin_class": "economy",
            }
        }

        data = await self._request_with_retry(
            "POST", f"{self._base_url}/air/offer_requests", payload
        )

        offers = data.get("offers", [])
        if not offers:
            return None

        cheapest = min(offers, key=lambda o: Decimal(o.get("total_amount", "999999")))
        return self._build_result(cheapest, origin, destination, depart_date, return_date)

    async def search_cheapest_dates(
        self, origin: str, destination: str, start_date: date, end_date: date
    ) -> list[FlightResult]:
        result = await self.search_flights(
            origin, destination, start_date, start_date + timedelta(days=5)
        )
        if result:
            return [result]
        return []

    async def _request_with_retry(
        self, method: str, url: str, payload: dict
    ) -> dict:
        last_error: ProviderError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._do_request(method, url, payload)
            except ProviderError as e:
                last_error = e
                if not e.retryable or attempt == self._max_retries:
                    raise
                backoff = 2 ** attempt
                await asyncio.sleep(backoff)
        raise last_error  # type: ignore[misc]

    async def _do_request(
        self, method: str, url: str, payload: dict
    ) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.request(
                    method, url, json=payload, headers=self._headers()
                )
        except httpx.TimeoutException:
            raise ProviderError(
                "duffel",
                ProviderErrorCode.TIMEOUT,
                retryable=True,
                detail="Request timed out",
            )

        if resp.status_code == 401:
            raise ProviderError(
                "duffel",
                ProviderErrorCode.AUTH_ERROR,
                retryable=False,
                status_code=401,
                detail="Invalid Duffel API token",
            )

        if resp.status_code == 429:
            raise ProviderError(
                "duffel",
                ProviderErrorCode.RATE_LIMITED,
                retryable=True,
                status_code=429,
                detail="Rate limited by Duffel API",
            )

        if resp.status_code >= 500:
            raise ProviderError(
                "duffel",
                ProviderErrorCode.UPSTREAM_ERROR,
                retryable=True,
                status_code=resp.status_code,
                detail=f"Duffel upstream error: {resp.status_code}",
            )

        try:
            body = resp.json()
        except Exception:
            raise ProviderError(
                "duffel",
                ProviderErrorCode.INVALID_RESPONSE,
                retryable=False,
                status_code=resp.status_code,
                detail="Malformed JSON response from Duffel",
            )

        if resp.status_code >= 400:
            raise ProviderError(
                "duffel",
                ProviderErrorCode.INVALID_RESPONSE,
                retryable=False,
                status_code=resp.status_code,
                detail=f"Duffel API error: {resp.status_code}",
            )

        return body.get("data", body)

    def _build_result(
        self,
        offer: dict,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date,
    ) -> FlightResult:
        total_amount = Decimal(offer.get("total_amount", "0"))
        total_currency = offer.get("total_currency", "USD")

        slices = offer.get("slices", [])
        airlines: set[str] = set()
        total_duration_min = 0
        max_stops = 0

        outbound_slice: FlightSlice | None = None
        inbound_slice: FlightSlice | None = None

        owner_name = offer.get("owner", {}).get("name")
        if owner_name:
            airlines.add(owner_name)

        for idx, sl in enumerate(slices):
            segments = sl.get("segments", [])
            seg_models: list[FlightSegment] = []
            for seg in segments:
                carrier_name = seg.get("marketing_carrier", {}).get("name")
                op_carrier = seg.get("operating_carrier", {}).get("name")
                if carrier_name:
                    airlines.add(carrier_name)
                if op_carrier:
                    airlines.add(op_carrier)

                departing_at = self._parse_datetime(seg.get("departing_at", ""))
                arriving_at = self._parse_datetime(seg.get("arriving_at", ""))
                seg_duration = self._parse_duration(seg.get("duration", "PT0M"))

                seg_models.append(
                    FlightSegment(
                        origin=seg.get("origin", {}).get("iata_code", ""),
                        destination=seg.get("destination", {}).get("iata_code", ""),
                        departing_at=departing_at,
                        arriving_at=arriving_at,
                        duration_minutes=seg_duration,
                        marketing_carrier=carrier_name,
                        operating_carrier=op_carrier,
                        flight_number=seg.get("flight_number"),
                    )
                )

            slice_duration = self._parse_duration(sl.get("duration", "PT0M"))
            slice_stops = max(len(segments) - 1, 0)
            total_duration_min += slice_duration
            max_stops = max(max_stops, slice_stops)

            flight_slice = FlightSlice(
                segments=seg_models,
                duration_minutes=slice_duration,
                stops=slice_stops,
            )

            if idx == 0:
                outbound_slice = flight_slice
            elif idx == 1:
                inbound_slice = flight_slice

        expires_at = self._parse_datetime(offer.get("expires_at", "")) or None
        fetched_at = datetime.now(timezone.utc)

        flight_offer = FlightOffer(
            provider="duffel",
            provider_offer_id=offer.get("id"),
            origin=origin,
            destination=destination,
            departure_date=depart_date,
            return_date=return_date,
            outbound=outbound_slice,
            inbound=inbound_slice,
            total_price=total_amount,
            currency=total_currency,
            airlines=sorted(airlines),
            expires_at=expires_at,
            fetched_at=fetched_at,
            source=SourceMetadata(provider="duffel", data_kind=DataKind.LIVE),
        )

        return FlightResult(
            origin=origin,
            destination=destination,
            departure_date=depart_date,
            return_date=return_date,
            price=float(total_amount),
            currency=total_currency,
            stops=max_stops,
            total_duration_min=total_duration_min,
            airline=", ".join(sorted(airlines)) if airlines else None,
            source="duffel",
            source_metadata=SourceMetadata(provider="duffel", data_kind=DataKind.LIVE),
            offer=flight_offer,
        )

    @staticmethod
    def _parse_duration(duration: str) -> int:
        minutes = 0
        hours = re.search(r"(\d+)H", duration)
        mins = re.search(r"(\d+)M", duration)
        if hours:
            minutes += int(hours.group(1)) * 60
        if mins:
            minutes += int(mins.group(1))
        return minutes

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
