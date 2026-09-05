"""Cliente HTTP común del ETL (spec secciones 2 y 6).

Retries ante errores transitorios con backoff exponencial; los errores
funcionales 4xx no se reintentan y quedan para que el llamador decida
semánticamente.
"""

import logging
import time
from typing import Optional

import httpx

from etl.config import (
    ETL_CONNECT_TIMEOUT_SECONDS,
    ETL_HTTP_USER_AGENT,
    ETL_MAX_RETRIES,
    ETL_READ_TIMEOUT_SECONDS,
)

logger = logging.getLogger("etl.http")

RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
DEFAULT_RETRY_BACKOFF_SECONDS = (1, 2, 4)

_TRANSIENT_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
)


class ExternalHttpClient:
    """Cliente sync con retries y timeouts predecibles."""

    def __init__(
        self,
        *,
        user_agent: str = ETL_HTTP_USER_AGENT,
        connect_timeout: float = ETL_CONNECT_TIMEOUT_SECONDS,
        read_timeout: float = ETL_READ_TIMEOUT_SECONDS,
        max_retries: int = ETL_MAX_RETRIES,
        retry_backoff=DEFAULT_RETRY_BACKOFF_SECONDS,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self._max_retries = max_retries
        self._retry_backoff = tuple(retry_backoff)
        self._client = httpx.Client(
            timeout=httpx.Timeout(read_timeout, connect=connect_timeout),
            headers={"User-Agent": user_agent},
            follow_redirects=True,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def get(self, url: str, *, params: Optional[dict] = None, timeout: Optional[float] = None) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.get(url, params=params, timeout=timeout)
            except _TRANSIENT_EXCEPTIONS as exc:
                if attempt >= self._max_retries:
                    raise httpx.TransportError(
                        f"GET {url} agotó reintentos sin respuesta"
                    ) from exc
                self._sleep_on_retry(attempt, url, reason=exc.__class__.__name__)
                continue

            if response.status_code not in RETRYABLE_STATUS_CODES:
                return response

            if attempt >= self._max_retries:
                raise httpx.HTTPStatusError(
                    f"GET {url} falló tras {self._max_retries + 1} intentos: {response.status_code}",
                    request=response.request,
                    response=response,
                )

            self._sleep_on_retry(attempt, url, reason=f"status={response.status_code}")

        raise httpx.TransportError(f"GET {url} no retornó respuesta")

    def _sleep_on_retry(self, attempt: int, url: str, *, reason: str) -> None:
        backoff = self._retry_backoff[min(attempt, len(self._retry_backoff) - 1)]
        logger.warning("http retry url=%s attempt=%s backoff=%ss reason=%s", url, attempt + 1, backoff, reason)
        time.sleep(backoff)


def get_json(http: ExternalHttpClient, url: str, *, params: Optional[dict] = None, timeout: Optional[float] = None) -> dict:
    """GET + raise por fallo funcional + parse JSON. Conveniencia para APIs JSON."""
    response = http.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()