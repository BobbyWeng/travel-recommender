from __future__ import annotations

import asyncio
import time
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AmadeusAuthClient:
    _instance: AmadeusAuthClient | None = None
    _lock = asyncio.Lock()

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

    @classmethod
    def get_instance(cls) -> AmadeusAuthClient:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        async with self._lock:
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
                logger.info("Amadeus token refreshed")
                return self._access_token
