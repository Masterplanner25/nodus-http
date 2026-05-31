# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.1.0] — 2026-05-31

Initial release — prepared, not yet published.

### Added

- **`HttpClient`** — `httpx` wrapper with optional circuit breaker, retry, and
  trace header injection. Constructor args: `base_url`, `timeout`,
  `default_headers`, `retry_config`, `circuit_breaker`, `get_trace_id_fn`.
  Sync methods: `get`, `post`, `put`, `delete`, `request`.
  Async methods: `get_async`, `post_async`, `put_async`, `delete_async`,
  `request_async`.

- **`HttpResponse`** — normalised response. Fields: `status_code`, `headers`,
  `body` (bytes). Properties: `ok` (2xx bool), `text` (decoded str).
  Method: `json()` (parsed body).

- **`RetryConfig`** — retry settings. Fields: `max_attempts` (default 1 — no
  retry), `retryable_status_codes` (set, default `{429, 502, 503, 504}`),
  `backoff_ms` (default 0), `exponential` (bool, default False).
  Retries on network errors and retryable status codes only.

- **`inject_trace_headers(headers, get_trace_id_fn)`** — adds `X-Trace-ID`
  to a headers dict using the result of `get_trace_id_fn()`. No-op if
  `get_trace_id_fn` is `None` or returns `None`.

- **13 tests** in `tests/test_http.py`. Uses `respx` for request mocking.

- **One required dependency:** `httpx>=0.24.0`. Optional extras:
  `[circuit-breaker]`, `[otel]`, `[retry]`.

[0.1.0]: https://github.com/Masterplanner25/nodus-http/releases/tag/v0.1.0
