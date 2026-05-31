"""Trace header injection for distributed tracing."""
from __future__ import annotations

from typing import Callable, Optional


def inject_trace_headers(
    headers: dict[str, str],
    *,
    get_trace_id_fn: Optional[Callable[[], Optional[str]]] = None,
) -> dict[str, str]:
    """Return *headers* with X-Trace-ID injected if a trace ID is available.

    Args:
        headers:           Existing headers dict (not mutated).
        get_trace_id_fn:   Zero-argument callable returning current trace ID.
                           When None or returns None, no header is injected.
    """
    if get_trace_id_fn is None:
        return headers
    trace_id = get_trace_id_fn()
    if not trace_id:
        return headers
    return {**headers, "X-Trace-ID": trace_id}
