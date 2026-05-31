"""nodus-http tests using respx to mock HTTPX."""
import pytest
import respx
import httpx

from nodus_http import HttpClient, HttpResponse, RetryConfig, inject_trace_headers


# ── HttpResponse ──────────────────────────────────────────────────────────────

def test_response_ok():
    r = HttpResponse(status_code=200, headers={}, body=b"ok")
    assert r.ok is True


def test_response_not_ok():
    r = HttpResponse(status_code=404, headers={}, body=b"not found")
    assert r.ok is False


def test_response_server_error_not_ok():
    r = HttpResponse(status_code=500, headers={}, body=b"err")
    assert r.ok is False


# ── RetryConfig ───────────────────────────────────────────────────────────────

def test_retry_config_defaults():
    rc = RetryConfig()
    assert rc.max_attempts == 3
    assert 429 in rc.retryable_status_codes
    assert 500 in rc.retryable_status_codes


# ── inject_trace_headers ──────────────────────────────────────────────────────

def test_inject_no_fn():
    h = inject_trace_headers({"Accept": "application/json"})
    assert "X-Trace-ID" not in h
    assert h["Accept"] == "application/json"


def test_inject_with_fn():
    h = inject_trace_headers({}, get_trace_id_fn=lambda: "trace-abc")
    assert h["X-Trace-ID"] == "trace-abc"


def test_inject_fn_returns_none():
    h = inject_trace_headers({"k": "v"}, get_trace_id_fn=lambda: None)
    assert "X-Trace-ID" not in h


def test_inject_does_not_mutate_original():
    orig = {"k": "v"}
    inject_trace_headers(orig, get_trace_id_fn=lambda: "t1")
    assert "X-Trace-ID" not in orig


# ── HttpClient basic operations ───────────────────────────────────────────────

@respx.mock
def test_get_success():
    respx.get("https://api.example.com/items").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    client = HttpClient(base_url="https://api.example.com", retry=RetryConfig(max_attempts=1))
    resp = client.get("/items")
    assert resp.status_code == 200
    assert resp.ok is True
    assert resp.json == {"items": []}


@respx.mock
def test_post_json():
    respx.post("https://api.example.com/data").mock(
        return_value=httpx.Response(201, json={"id": "new"})
    )
    client = HttpClient(base_url="https://api.example.com", retry=RetryConfig(max_attempts=1))
    resp = client.post("/data", json={"name": "test"})
    assert resp.status_code == 201
    assert resp.json["id"] == "new"


@respx.mock
def test_trace_id_injected():
    captured_headers = {}

    def capture(request, route):
        captured_headers.update(dict(request.headers))
        return httpx.Response(200, json={})

    respx.get("https://api.example.com/x").mock(side_effect=capture)
    client = HttpClient(
        base_url="https://api.example.com",
        retry=RetryConfig(max_attempts=1),
        get_trace_id_fn=lambda: "my-trace-id",
    )
    client.get("/x")
    assert captured_headers.get("x-trace-id") == "my-trace-id"


@respx.mock
def test_client_retries_on_500():
    call_count = 0

    def handler(request, route):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return httpx.Response(500, text="error")
        return httpx.Response(200, json={"ok": True})

    respx.get("https://api.example.com/retry-me").mock(side_effect=handler)
    client = HttpClient(
        base_url="https://api.example.com",
        retry=RetryConfig(max_attempts=3, backoff_ms=0, retryable_status_codes=(500,)),
    )
    resp = client.get("/retry-me")
    assert resp.ok is True
    assert call_count == 3


@respx.mock
def test_circuit_breaker_used():
    from nodus_circuit_breaker import CircuitBreaker
    cb = CircuitBreaker("test", failure_threshold=5)

    respx.get("https://api.example.com/cb").mock(
        return_value=httpx.Response(200, json={})
    )
    client = HttpClient(
        base_url="https://api.example.com",
        retry=RetryConfig(max_attempts=1),
        circuit_breaker=cb,
    )
    resp = client.get("/cb")
    assert resp.ok is True
    assert cb.state.value == "closed"
