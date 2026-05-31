"""HTTP retry configuration."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetryConfig:
    """Configuration for HTTP request retry behaviour.

    Attributes
    ----------
    max_attempts:          Total attempts (1 = no retry).
    retryable_status_codes: HTTP status codes that trigger a retry.
    backoff_ms:            Base delay in milliseconds.
    exponential:           When True, double backoff_ms on each retry.
    """

    max_attempts: int = 3
    retryable_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)
    backoff_ms: int = 200
    exponential: bool = True


def is_retryable_status(status_code: int, config: RetryConfig) -> bool:
    return status_code in config.retryable_status_codes
