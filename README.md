# nodus-http

**Outbound HTTP client with circuit breaker, retry, and OTel trace propagation.**

Wraps `httpx` with optional circuit-breaker protection, configurable retry
logic, and trace ID header injection. All integrations are constructor-injected
— no globals or module-level configuration.

> **Status:** v0.1.0 — published on [PyPI](https://pypi.org/project/nodus-http/).

---

## Install

```bash
pip install nodus-http

# With circuit breaker:
pip install "nodus-http[circuit-breaker]"

# With OTel trace propagation:
pip install "nodus-http[otel]"
```

---

## What it provides

| Component | Purpose |
|---|---|
| `HttpClient` | `httpx` wrapper with circuit breaker, retry, and trace headers |
| `HttpResponse` | Normalised response: `status_code`, `headers`, `body`, `json()`, `ok` |
| `RetryConfig` | Retry settings: max attempts, retryable status codes, backoff |
| `inject_trace_headers` | Add `X-Trace-ID` to a headers dict via callback |

---

## Quick start

```python
from nodus_http import HttpClient

client = HttpClient(base_url="https://api.example.com", timeout=10.0)
response = client.get("/users/123")

if response.ok:
    data = response.json()
```

---

## HttpClient

```python
from nodus_http import HttpClient, RetryConfig
from nodus_circuit_breaker import CircuitBreaker

client = HttpClient(
    base_url="https://api.example.com",
    timeout=10.0,
    default_headers={"Authorization": "Bearer my-token"},
    retry_config=RetryConfig(
        max_attempts=3,
        retryable_status_codes={429, 502, 503, 504},
        backoff_ms=200,
        exponential=True,
    ),
    circuit_breaker=CircuitBreaker("api.example.com", failure_threshold=5),
    get_trace_id_fn=lambda: my_context.trace_id,  # optional
)

# Sync
response = client.get("/path")
response = client.post("/path", json={"key": "value"})
response = client.put("/path", json={...})
response = client.delete("/path")
response = client.request("PATCH", "/path", json={...})

# Async
response = await client.get_async("/path")
response = await client.post_async("/path", json={...})
```

---

## HttpResponse

```python
response.ok           # True if 2xx
response.status_code  # int
response.headers      # dict
response.body         # bytes
response.json()       # parsed JSON (dict | list | ...)
response.text         # decoded string
```

---

## RetryConfig

```python
from nodus_http import RetryConfig

config = RetryConfig(
    max_attempts=3,
    retryable_status_codes={429, 502, 503, 504},
    backoff_ms=100,
    exponential=True,   # doubles each attempt: 100ms, 200ms, 400ms
)
```

Retries fire on network errors and on responses with a retryable status code.
Non-retryable errors (4xx except those in `retryable_status_codes`) are not
retried.

---

## Trace header injection

```python
from nodus_http import inject_trace_headers

headers = {"Content-Type": "application/json"}
headers = inject_trace_headers(headers, get_trace_id_fn=lambda: "trace-abc")
# headers now includes "X-Trace-ID": "trace-abc"
```

Pass `get_trace_id_fn` to `HttpClient` to inject the trace ID automatically
on every request.

---

## Circuit breaker

Pass any object with a `.call(fn)` method as `circuit_breaker`. The
`nodus-circuit-breaker` package provides a compatible `CircuitBreaker`:

```bash
pip install "nodus-http[circuit-breaker]"
```

```python
from nodus_circuit_breaker import CircuitBreaker

cb = CircuitBreaker("my-api", failure_threshold=3, recovery_timeout_secs=30)
client = HttpClient("https://api.example.com", circuit_breaker=cb)
```

When the circuit is open, `client.get(...)` raises `CircuitOpenError`.

---

## Design

- **`httpx` required.** All other integrations (circuit breaker, retry, trace)
  are injected and optional.
- **No globals.** All configuration is per-`HttpClient` instance.
- **Normalised response.** `HttpResponse` wraps httpx responses with a
  consistent interface regardless of sync/async path.

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -q
```

Tests use `respx` for request mocking.

---

## License

MIT — see [LICENSE](LICENSE).
