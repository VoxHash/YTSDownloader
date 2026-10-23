"""Shared helpers."""

from __future__ import annotations

import re
from typing import List
from urllib.parse import urlparse

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def clean_filename(filename: str) -> str:
    valid_chars = (
        "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789áéíóúÁÉÍÓÚñÑ#"
    )
    return "".join(c for c in filename if c in valid_chars)


def extract_urls(text: str) -> List[str]:
    """Pull unique http(s) URLs from free text (paste, drop, or file contents)."""
    if not text or not text.strip():
        return []
    seen = set()
    out: List[str] = []
    for match in _URL_RE.finditer(text):
        raw = match.group(0).rstrip(").,;]'\"")
        parsed = urlparse(raw)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        if raw in seen:
            continue
        seen.add(raw)
        out.append(raw)
    return out
