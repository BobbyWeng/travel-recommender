from __future__ import annotations

from enum import Enum


class ProviderErrorCode(str, Enum):
    AUTH_ERROR = "AUTH_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    NO_RESULTS = "NO_RESULTS"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class ProviderError(Exception):
    def __init__(
        self,
        provider: str,
        code: ProviderErrorCode,
        retryable: bool = False,
        status_code: int | None = None,
        detail: str | None = None,
    ):
        self.provider = provider
        self.code = code
        self.retryable = retryable
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"[{provider}] {code.value}: {detail or 'no detail'}")
