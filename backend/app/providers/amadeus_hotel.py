from __future__ import annotations

import time

import httpx

from app.core.config import settings
from app.providers.base import HotelProvider
from app.schemas.search import HotelResult


class AmadeusHotelProvider(HotelProvider):
    def __init__(self):
        self._client_id = settings.AMADEUS_CLIENT_ID
        self._client_secret = settings.AMADEUS_CLIENT_SECRET
        self._env = settings.AMADEUS_ENV
        self._access_token: str | None = None
        self._token_expires_at: float = 0
        self._base_url = (
            "https://test.api.amadeus.com"
            if self._env == "sandbox"
            else "https://api.amadeus.com"
        )

    async def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        if not self._client_id or not self._client_secret:
            raise ValueError("Amadeus API credentials not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            self._token_expires_at = time.time() + data.get("expires_in", 1800) - 60
            return self._access_token

    async def search_hotels(
        self, city_iata: str, check_in, check_out, adults: int = 2
    ) -> HotelResult | None:
        try:
            token = await self._get_access_token()
        except Exception:
            return None

        nights = (check_out - check_in).days
        if nights <= 0:
            return None

        params = {
            "cityCode": city_iata,
            "checkInDate": check_in.isoformat(),
            "checkOutDate": check_out.isoformat(),
            "adults": adults,
            "currency": "USD",
            "bestRateOnly": "true",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self._base_url}/v3/shopping/hotel-offers",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code in (429, 404):
                    return None
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, httpx.TimeoutException):
            return None

        offers = data.get("data", [])
        if not offers:
            return None

        prices = []
        for offer_data in offers:
            offers_list = offer_data.get("offers", [])
            for o in offers_list:
                price_info = o.get("price", {})
                total_str = price_info.get("total")
                if total_str:
                    try:
                        prices.append(float(total_str))
                    except (ValueError, TypeError):
                        continue

        if not prices:
            return None

        prices.sort()
        median_price = prices[len(prices) // 2]
        nightly_price = round(median_price / nights, 2)

        return HotelResult(
            destination_iata=city_iata,
            check_in=check_in,
            check_out=check_out,
            nightly_price=nightly_price,
            total_price=round(median_price, 2),
            currency="USD",
            hotel_class=3.0,
            area="city center",
            source="amadeus",
        )
