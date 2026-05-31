"""HttpClient — HTTPX wrapper with circuit breaker, retry, and trace propagation."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

try:
    import httpx as _httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _httpx = None  # type: ignore[assignment]
    _HTTPX_AVAILABLE = False


@dataclass
class HttpResponse:
    """Normalised HTTP response.

    Attributes
    ----------
    status_code: HTTP status code.
    headers:     Response headers as a plain dict.
    body:        Raw response bytes.
    json:        Decoded JSON body (when Content-Type contains ``"json"``).
    """

    status_code: int
    headers: dict[str, str]
    body: bytes
    json: Optional[dict[str, Any]] = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class HttpClient:
    """HTTPX wrapper with circuit breaker, retry, and OTel trace propagation.

    All dependencies are optional — the client degrades gracefully:
    - No ``circuit_breaker``: requests go through without circuit protection.
    - No ``get_trace_id_fn``: ``X-Trace-ID`` is not injected.
    - No ``retry``: a single attempt is made.

    Args:
        base_url:         Optional URL prefix for all requests.
        timeout:          Request timeout in seconds (default: 30).
        retry:            ``RetryConfig`` for status-code-based retry.
        circuit_breaker:  A ``CircuitBreaker`` from ``nodus-circuit-breaker``.
        get_trace_id_fn:  ``() → str | None`` for trace header injection.
        default_headers:  Headers sent with every request.
    """

    def __init__(
        self,
        *,
        base_url: str = "",
        timeout: float = 30.0,
        retry: Optional["RetryConfig"] = None,
        circuit_breaker: Optional[Any] = None,
        get_trace_id_fn: Optional[Callable[[], Optional[str]]] = None,
        default_headers: Optional[dict[str, str]] = None,
    ) -> None:
        if not _HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for HttpClient. "
                "Install with: pip install nodus-http"
            )
        from .retry import RetryConfig  # noqa: PLC0415
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retry = retry or RetryConfig(max_attempts=1)
        self._circuit_breaker = circuit_breaker
        self._get_trace_id = get_trace_id_fn
        self._default_headers = dict(default_headers or {})

    def _url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return f"{self._base_url}{path}"

    def _build_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        from .trace import inject_trace_headers  # noqa: PLC0415
        headers = {**self._default_headers, **(extra or {})}
        return inject_trace_headers(headers, get_trace_id_fn=self._get_trace_id)

    def _parse_response(self, resp: Any) -> HttpResponse:
        headers = dict(resp.headers)
        body = resp.content
        json_body: Optional[dict] = None
        content_type = headers.get("content-type", "")
        if "json" in content_type:
            try:
                json_body = resp.json()
            except Exception:
                pass
        return HttpResponse(
            status_code=resp.status_code,
            headers=headers,
            body=body,
            json=json_body,
        )

    def _execute(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        from .retry import is_retryable_status  # noqa: PLC0415
        import random  # noqa: PLC0415

        last_exc: Optional[Exception] = None
        for attempt in range(self._retry.max_attempts):
            try:
                def _do_request():
                    with _httpx.Client(timeout=self._timeout) as c:
                        return getattr(c, method)(url, **kwargs)

                if self._circuit_breaker is not None:
                    raw = self._circuit_breaker.call(_do_request)
                else:
                    raw = _do_request()

                response = self._parse_response(raw)

                if response.ok or not is_retryable_status(response.status_code, self._retry):
                    return response

                # Retryable status — sleep and retry
                if attempt + 1 < self._retry.max_attempts:
                    multiplier = 2 ** attempt if self._retry.exponential else 1
                    delay_ms = self._retry.backoff_ms * multiplier + random.randint(0, 50)
                    logger.debug(
                        "[nodus-http] retryable status=%d; sleeping %.2fs",
                        response.status_code, delay_ms / 1000,
                    )
                    time.sleep(delay_ms / 1000.0)

                last_exc = Exception(f"HTTP {response.status_code}")
                continue

            except Exception as exc:
                last_exc = exc
                if attempt + 1 < self._retry.max_attempts:
                    multiplier = 2 ** attempt if self._retry.exponential else 1
                    delay_ms = self._retry.backoff_ms * multiplier
                    time.sleep(delay_ms / 1000.0)

        raise last_exc or RuntimeError("Request failed after all attempts")

    def get(self, path: str, *, headers: dict | None = None,
            params: dict | None = None) -> HttpResponse:
        return self._execute(
            "get", self._url(path),
            headers=self._build_headers(headers),
            params=params,
        )

    def post(self, path: str, *, json: Any = None, data: Any = None,
             headers: dict | None = None) -> HttpResponse:
        kwargs: dict[str, Any] = {"headers": self._build_headers(headers)}
        if json is not None:
            kwargs["json"] = json
        if data is not None:
            kwargs["content"] = data
        return self._execute("post", self._url(path), **kwargs)

    def put(self, path: str, *, json: Any = None,
            headers: dict | None = None) -> HttpResponse:
        kwargs: dict[str, Any] = {"headers": self._build_headers(headers)}
        if json is not None:
            kwargs["json"] = json
        return self._execute("put", self._url(path), **kwargs)

    def delete(self, path: str, *, headers: dict | None = None) -> HttpResponse:
        return self._execute(
            "delete", self._url(path), headers=self._build_headers(headers)
        )

    async def get_async(self, path: str, *, headers: dict | None = None,
                        params: dict | None = None) -> HttpResponse:
        async with _httpx.AsyncClient(timeout=self._timeout) as c:
            raw = await c.get(
                self._url(path),
                headers=self._build_headers(headers),
                params=params,
            )
        return self._parse_response(raw)

    async def post_async(self, path: str, *, json: Any = None,
                         headers: dict | None = None) -> HttpResponse:
        kwargs: dict[str, Any] = {"headers": self._build_headers(headers)}
        if json is not None:
            kwargs["json"] = json
        async with _httpx.AsyncClient(timeout=self._timeout) as c:
            raw = await c.post(self._url(path), **kwargs)
        return self._parse_response(raw)
