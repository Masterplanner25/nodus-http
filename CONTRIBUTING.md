# Contributing to nodus-http

## Setup

```bash
git clone https://github.com/Masterplanner25/nodus-http.git
cd nodus-http
pip install -e ".[dev]"
```

The `dev` extra includes `respx` for request mocking and `nodus-circuit-breaker`
for circuit breaker integration tests.

## Running tests

```bash
pytest tests/ -q
```

## Code style

- Python 3.11+
- `httpx` is the one required dependency — all other integrations are injected
- `circuit_breaker`, `retry_config`, `get_trace_id_fn` are all optional
  constructor args — never require them
- Use `respx` for mocking HTTP responses in tests

## Submitting changes

1. Fork the repo and create a branch from `main`
2. Add tests for any new behaviour
3. Ensure `pytest tests/ -q` passes
4. Open a pull request with a description of what changes and why
