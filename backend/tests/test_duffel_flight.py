import asyncio
import json
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import settings
from app.providers.duffel_flight import DuffelFlightProvider
from app.providers.errors import ProviderError, ProviderErrorCode
from app.schemas.search import DataKind


def _make_duffel_response(offers=None):
    if offers is None:
        offers = []
    return {
        "data": {
            "id": "orq_123",
            "offers": offers,
            "slices": [],
            "passengers": [{"id": "pas_1", "type": "adult"}],
        }
    }


def _make_offer(
    total_amount="350.00",
    total_currency="USD",
    slices=None,
    expires_at=None,
    owner_name="Delta",
):
    if slices is None:
        slices = [_make_slice("ATL", "SFO", "2026-09-20"), _make_slice("SFO", "ATL", "2026-09-25")]
    return {
        "id": "off_123",
        "total_amount": total_amount,
        "total_currency": total_currency,
        "slices": slices,
        "expires_at": expires_at or "2026-09-20T23:59:59Z",
        "owner": {"name": owner_name},
        "passengers": [{"passenger_id": "pas_1"}],
        "available_services": [],
    }


def _make_slice(origin, destination, departure_date, segments=None):
    if segments is None:
        segments = [_make_segment(origin, destination, departure_date)]
    return {
        "origin": {"iata_code": origin},
        "destination": {"iata_code": destination},
        "departure_date": departure_date,
        "duration": "PT5H30M",
        "segments": segments,
    }


def _make_segment(origin, destination, departure_date, arriving_date=None, marketing_carrier="DL", flight_number="DL123"):
    return {
        "origin": {"iata_code": origin},
        "destination": {"iata_code": destination},
        "departing_at": f"{departure_date}T08:00:00Z",
        "arriving_at": arriving_date or f"{departure_date}T13:30:00Z",
        "marketing_carrier": {"name": marketing_carrier, "iata_code": marketing_carrier},
        "operating_carrier": {"name": marketing_carrier, "iata_code": marketing_carrier},
        "flight_number": flight_number,
        "duration": "PT5H30M",
    }


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="error", request=MagicMock(), response=resp
        )
    return resp


@pytest.fixture
def provider():
    original_token = settings.DUFFEL_ACCESS_TOKEN
    original_enabled = settings.DUFFEL_ENABLED
    settings.DUFFEL_ACCESS_TOKEN = "test_token"
    settings.DUFFEL_ENABLED = True
    settings.DUFFEL_MAX_RETRIES = 3
    settings.DUFFEL_TIMEOUT_SECONDS = 30
    p = DuffelFlightProvider()
    yield p
    settings.DUFFEL_ACCESS_TOKEN = original_token
    settings.DUFFEL_ENABLED = original_enabled


class TestDuffelNormalRoundTrip:
    @pytest.mark.asyncio
    async def test_direct_flight(self, provider):
        response_data = _make_duffel_response([_make_offer()])
        mock_resp = _mock_response(json_data=response_data)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert result is not None
        assert result.origin == "ATL"
        assert result.destination == "SFO"
        assert result.price == 350.0
        assert result.stops == 0
        assert result.source == "duffel"
        assert result.offer is not None
        assert result.offer.outbound is not None
        assert result.offer.inbound is not None
        assert len(result.offer.outbound.segments) == 1
        assert len(result.offer.inbound.segments) == 1


class TestDuffelMultiSegment:
    @pytest.mark.asyncio
    async def test_one_stop_outbound(self, provider):
        segments = [
            _make_segment("ATL", "ORD", "2026-09-20", arriving_date="2026-09-20T10:00:00Z"),
            _make_segment("ORD", "SFO", "2026-09-20", arriving_date="2026-09-20T14:30:00Z", marketing_carrier="UA", flight_number="UA456"),
        ]
        slices = [
            _make_slice("ATL", "SFO", "2026-09-20", segments=segments),
            _make_slice("SFO", "ATL", "2026-09-25"),
        ]
        response_data = _make_duffel_response([_make_offer(slices=slices)])
        mock_resp = _mock_response(json_data=response_data)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert result is not None
        assert result.stops == 1
        assert result.offer.outbound.stops == 1
        assert len(result.offer.outbound.segments) == 2


class TestDuffelEmptyResults:
    @pytest.mark.asyncio
    async def test_no_offers(self, provider):
        response_data = _make_duffel_response([])
        mock_resp = _mock_response(json_data=response_data)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert result is None


class TestDuffelRateLimitedRetry:
    @pytest.mark.asyncio
    async def test_429_then_success(self, provider):
        rate_limit_resp = _mock_response(status_code=429)
        success_data = _make_duffel_response([_make_offer()])
        success_resp = _mock_response(json_data=success_data)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(side_effect=[rate_limit_resp, success_resp])
            mock_client_cls.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert result is not None
        assert result.price == 350.0


class TestDuffelAuthError:
    @pytest.mark.asyncio
    async def test_401_no_retry(self, provider):
        auth_resp = _mock_response(status_code=401)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=auth_resp)
            mock_client_cls.return_value = mock_client

            with pytest.raises(ProviderError) as exc_info:
                await provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert exc_info.value.code == ProviderErrorCode.AUTH_ERROR
        assert exc_info.value.retryable is False
        assert mock_client.request.call_count == 1


class TestDuffelServerError:
    @pytest.mark.asyncio
    async def test_5xx_retry_then_fail(self, provider):
        provider._max_retries = 2
        server_resp = _mock_response(status_code=500)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=server_resp)
            mock_client_cls.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(ProviderError) as exc_info:
                    await provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert exc_info.value.code == ProviderErrorCode.UPSTREAM_ERROR
        assert exc_info.value.retryable is True
        assert mock_client.request.call_count == 3


class TestDuffelTimeout:
    @pytest.mark.asyncio
    async def test_timeout_raises_provider_error(self, provider):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client_cls.return_value = mock_client

            with pytest.raises(ProviderError) as exc_info:
                await provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert exc_info.value.code == ProviderErrorCode.TIMEOUT
        assert exc_info.value.retryable is True


class TestDuffelMalformedJson:
    @pytest.mark.asyncio
    async def test_malformed_response(self, provider):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("bad json")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            with pytest.raises(ProviderError) as exc_info:
                await provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert exc_info.value.code == ProviderErrorCode.INVALID_RESPONSE
        assert exc_info.value.retryable is False


class TestDuffelExpiresAt:
    @pytest.mark.asyncio
    async def test_expires_at_parsed(self, provider):
        offer = _make_offer(expires_at="2026-09-21T12:00:00Z")
        response_data = _make_duffel_response([offer])
        mock_resp = _mock_response(json_data=response_data)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert result is not None
        assert result.offer.expires_at is not None
        assert result.offer.expires_at.year == 2026
        assert result.offer.expires_at.month == 9
        assert result.offer.expires_at.day == 21


class TestDuffelDecimalPrice:
    @pytest.mark.asyncio
    async def test_decimal_price_parsing(self, provider):
        offer = _make_offer(total_amount="1234.56", total_currency="EUR")
        response_data = _make_duffel_response([offer])
        mock_resp = _mock_response(json_data=response_data)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert result is not None
        assert result.price == 1234.56
        assert result.currency == "EUR"
        assert result.offer.total_price == Decimal("1234.56")


class TestDuffelSourceMetadata:
    @pytest.mark.asyncio
    async def test_metadata_set_correctly(self, provider):
        response_data = _make_duffel_response([_make_offer()])
        mock_resp = _mock_response(json_data=response_data)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert result is not None
        assert result.source_metadata is not None
        assert result.source_metadata.provider == "duffel"
        assert result.source_metadata.data_kind == DataKind.LIVE
        assert result.offer.source is not None
        assert result.offer.source.provider == "duffel"
        assert result.offer.source.data_kind == DataKind.LIVE


class TestDuffelCheapestSelection:
    @pytest.mark.asyncio
    async def test_selects_cheapest_offer(self, provider):
        offers = [
            _make_offer(total_amount="500.00"),
            _make_offer(total_amount="200.00"),
            _make_offer(total_amount="350.00"),
        ]
        response_data = _make_duffel_response(offers)
        mock_resp = _mock_response(json_data=response_data)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await provider.search_flights("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert result is not None
        assert result.price == 200.0


class TestDuffelSearchCheapestDates:
    @pytest.mark.asyncio
    async def test_cheapest_dates_returns_result(self, provider):
        response_data = _make_duffel_response([_make_offer()])
        mock_resp = _mock_response(json_data=response_data)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            results = await provider.search_cheapest_dates("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert len(results) == 1
        assert results[0].price == 350.0

    @pytest.mark.asyncio
    async def test_cheapest_dates_no_results(self, provider):
        response_data = _make_duffel_response([])
        mock_resp = _mock_response(json_data=response_data)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            results = await provider.search_cheapest_dates("ATL", "SFO", date(2026, 9, 20), date(2026, 9, 25))

        assert results == []
