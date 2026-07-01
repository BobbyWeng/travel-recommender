from __future__ import annotations

import httpx

from app.providers.amadeus_auth import AmadeusAuthClient
from app.providers.base import HotelProvider
from app.schemas.search import HotelResult, SourceMetadata, DataKind


class AmadeusHotelProvider(HotelProvider):
    def __init__(self):
        self._auth = AmadeusAuthClient.get_instance()
        self._env = self._auth._env
        self._base_url = self._auth._base_url

    async def search_hotels(
        self, city_iata: str, check_in, check_out, adults: int = 2
    ) -> HotelResult | None:
        try:
            token = await self._auth.get_access_token()
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
            source_metadata=SourceMetadata(provider="amadeus", data_kind=DataKind.LIVE),
        )
