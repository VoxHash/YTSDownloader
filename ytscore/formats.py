"""yt-dlp format expressions and resilient fallbacks for Suite downloads."""

from __future__ import annotations

import re
from typing import Optional, Sequence

# Prefer separate A/V streams (ffmpeg merge) but accept progressive / unknown-codec
# variants when a strict bestvideo+bestaudio pair is missing (YouTube SABR, etc.).
DEFAULT_VIDEO_FORMAT = "bestvideo*+bestaudio/bestvideo+bestaudio/bv*+ba/b"
# Used when the configured VIDEO_FORMAT raises "format is not available".
RESILIENT_VIDEO_FORMAT = DEFAULT_VIDEO_FORMAT

# Prefer H.264 + AAC in mp4 containers when merge_output_format is set.
DEFAULT_FORMAT_SORT: Sequence[str] = (
    "res",
    "ext:mp4:m4a",
    "vcodec:h264",
    "acodec:aac",
    "br",
)

_FORMAT_UNAVAILABLE_RE = re.compile(
    r"format is not available|requested format|no video formats|only images are available",
    re.IGNORECASE,
)

# Legacy / brittle expressions we silently upgrade when still the configured default.
_LEGACY_VIDEO_FORMATS = frozenset(
    {
        "bestvideo+bestaudio/best",
        "bestvideo+bestaudio",
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
    }
)


def normalize_video_format(pref: str) -> str:
    """Return a usable video format string; upgrade known brittle defaults."""
    text = (pref or "").strip()
    if not text or text in _LEGACY_VIDEO_FORMATS:
        return DEFAULT_VIDEO_FORMAT
    return text


def is_format_unavailable_error(exc: object) -> bool:
    """True when yt-dlp failed because the selected format expression matched nothing."""
    return bool(_FORMAT_UNAVAILABLE_RE.search(str(exc or "")))


def next_format_fallback(current: str) -> Optional[str]:
    """
    Return a more resilient format expression to try after a format failure.

    Returns None when *current* is already the resilient default (nothing left to try).
    """
    cur = (current or "").strip()
    if not cur or cur == RESILIENT_VIDEO_FORMAT:
        return None
    if cur in _LEGACY_VIDEO_FORMATS:
        return RESILIENT_VIDEO_FORMAT
    # Custom user expression still failed — last resort resilient chain.
    return RESILIENT_VIDEO_FORMAT
