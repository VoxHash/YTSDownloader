"""Rate-limit detection and exponential backoff helpers."""

from __future__ import annotations

import re
from typing import Union

ErrorLike = Union[BaseException, str, None]

# HTTP 429 / quota / temporary extractor signals commonly seen via yt-dlp.
_RATE_LIMIT_RE = re.compile(
    r"(?i)(?:"
    r"\b429\b|"
    r"too many requests|"
    r"rate[-\s]?limit|"
    r"ratelimit|"
    r"quota exceeded|"
    r"http error 429|"
    r"retry[-\s]?after|"
    r"slow down|"
    r"temporar(?:y|ily) (?:unavailable|blocked)|"
    r"service unavailable|"
    r"\b503\b|"
    r"\b502\b|"
    r"\b500\b|"
    r"extractor error|"
    r"unable to download (?:webpage|api page)|"
    r"timed? ?out|"
    r"connection (?:reset|aborted|refused)"
    r")"
)

_HARD_RATE_LIMIT_RE = re.compile(
    r"(?i)(?:"
    r"\b429\b|"
    r"too many requests|"
    r"rate[-\s]?limit|"
    r"ratelimit|"
    r"quota exceeded|"
    r"http error 429|"
    r"retry[-\s]?after|"
    r"slow down"
    r")"
)


def _as_text(error: ErrorLike) -> str:
    if error is None:
        return ""
    if isinstance(error, BaseException):
        return f"{type(error).__name__}: {error}"
    return str(error)


def is_rate_limited(error: ErrorLike) -> bool:
    """True when the error looks like HTTP 429 / explicit rate limiting."""
    return bool(_HARD_RATE_LIMIT_RE.search(_as_text(error)))


def is_retryable_temporary(error: ErrorLike) -> bool:
    """True for rate limits and other temporary / flaky extractor failures."""
    return bool(_RATE_LIMIT_RE.search(_as_text(error)))


def compute_backoff_seconds(
    attempt: int,
    *,
    base: float = 2.0,
    factor: float = 2.0,
    maximum: float = 90.0,
    rate_limited: bool = False,
) -> float:
    """
    Exponential backoff for retry attempt ``attempt`` (1 = first retry after failure).

    Rate-limited failures use a longer base (2×) so playlist workers back off harder
    than generic transient errors.
    """
    if attempt < 1:
        attempt = 1
    base = max(0.0, float(base))
    factor = max(1.0, float(factor))
    maximum = max(0.0, float(maximum))
    effective_base = base * 2.0 if rate_limited else base
    delay = effective_base * (factor ** (attempt - 1))
    if maximum > 0:
        delay = min(maximum, delay)
    return max(0.0, delay)
