"""Classify download failures for the Queue triage panel."""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from ytscore.backoff import ErrorLike, is_rate_limited, is_retryable_temporary


class FailureCategory(str, Enum):
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    NETWORK = "network"
    UNAVAILABLE = "unavailable"
    FORMAT = "format"
    UNKNOWN = "unknown"


CATEGORY_LABELS = {
    FailureCategory.RATE_LIMIT: "Rate limit",
    FailureCategory.AUTH: "Auth / cookies",
    FailureCategory.NETWORK: "Network / temporary",
    FailureCategory.UNAVAILABLE: "Unavailable",
    FailureCategory.FORMAT: "Format / ffmpeg",
    FailureCategory.UNKNOWN: "Unknown",
}


def _error_text(error: ErrorLike) -> str:
    if error is None:
        return ""
    if isinstance(error, BaseException):
        return f"{type(error).__name__}: {error}"
    return str(error)


_AUTH_RE = re.compile(
    r"(?i)(?:"
    r"sign in|"
    r"login required|"
    r"not authorized|"
    r"unauthorized|"
    r"forbidden|"
    r"\b403\b|"
    r"cookies?|"
    r"age[-\s]?restrict|"
    r"confirm your age|"
    r"members?[-\s]?only|"
    r"private video|"
    r"this video is private|"
    r"bot check|"
    r"captcha"
    r")"
)

_UNAVAILABLE_RE = re.compile(
    r"(?i)(?:"
    r"\b404\b|"
    r"not found|"
    r"unavailable|"
    r"has been removed|"
    r"video has been deleted|"
    r"account has been terminated|"
    r"no video|"
    r"unsupported url|"
    r"is not a valid url"
    r")"
)

_FORMAT_RE = re.compile(
    r"(?i)(?:"
    r"ffmpeg|"
    r"ffprobe|"
    r"postprocessing|"
    r"requested format|"
    r"format is not available|"
    r"no suitable|"
    r"merge|"
    r"codec|"
    r"encoder|"
    r"moviepy|"
    r"watermark"
    r")"
)


def classify_failure(error: ErrorLike) -> FailureCategory:
    """Return a coarse category for a job error / message string."""
    text = _error_text(error).strip()
    if not text:
        return FailureCategory.UNKNOWN
    if is_rate_limited(error):
        return FailureCategory.RATE_LIMIT
    if _AUTH_RE.search(text):
        return FailureCategory.AUTH
    if _FORMAT_RE.search(text):
        return FailureCategory.FORMAT
    if _UNAVAILABLE_RE.search(text):
        return FailureCategory.UNAVAILABLE
    if is_retryable_temporary(error):
        return FailureCategory.NETWORK
    return FailureCategory.UNKNOWN


def category_label(category: FailureCategory) -> str:
    return CATEGORY_LABELS.get(category, CATEGORY_LABELS[FailureCategory.UNKNOWN])


def failure_detail_text(
    *,
    title: str = "",
    url: str = "",
    state: str = "",
    error: Optional[str] = None,
    message: str = "",
) -> str:
    """Human-readable block for the triage panel (category + fields)."""
    raw = (error or message or "").strip()
    cat = classify_failure(raw)
    lines = [
        f"Category: {category_label(cat)} ({cat.value})",
        f"State: {state or '—'}",
        f"Title: {title or '—'}",
        f"URL: {url or '—'}",
        "",
        "Detail:",
        raw or "(no error detail)",
    ]
    return "\n".join(lines)
