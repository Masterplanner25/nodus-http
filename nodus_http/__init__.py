"""nodus-http — outbound HTTP client with circuit breaker, retry, and trace propagation.

Client:
    HttpClient    — HTTPX wrapper; pass circuit_breaker / retry / get_trace_id_fn
    HttpResponse  — normalised response (status_code, headers, body, json, ok)

Retry:
    RetryConfig   — max_attempts, retryable_status_codes, backoff_ms, exponential

Trace:
    inject_trace_headers — add X-Trace-ID to headers via callback
"""
from .client import HttpClient, HttpResponse
from .retry import RetryConfig
from .trace import inject_trace_headers

__all__ = [
    "HttpClient",
    "HttpResponse",
    "RetryConfig",
    "inject_trace_headers",
]
