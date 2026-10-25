"""Shared helpers."""

from __future__ import annotations

import html
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse, urlunparse

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def clean_filename(filename: str) -> str:
    valid_chars = (
        "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789áéíóúÁÉÍÓÚñÑ#"
    )
    return "".join(c for c in filename if c in valid_chars)


def canonicalize_media_url(
    url: str,
    *,
    base_url: Optional[str] = None,
    prefer_https: bool = True,
) -> str:
    """
    Normalize extractor / paste URLs for enqueue and download.

    Unescapes HTML entities (``&amp;``), joins relative paths against an optional
    base, strips trailing punctuation noise, and upgrades ``http://`` → ``https://``
    when requested.
    """
    text = html.unescape((url or "").strip()).rstrip(").,;]'\"")
    if not text:
        return ""
    if base_url and not text.startswith(("http://", "https://", "//")):
        text = urljoin(base_url, text)
    if text.startswith("//"):
        text = "https:" + text
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return text
    scheme = "https" if prefer_https and parsed.scheme == "http" else parsed.scheme
    # Drop fragment; keep query (view keys / playlist keys).
    return urlunparse(
        (scheme, parsed.netloc.lower(), parsed.path, parsed.params, parsed.query, "")
    )


def extract_urls(text: str) -> List[str]:
    """Pull unique http(s) URLs from free text (paste, drop, or file contents)."""
    if not text or not text.strip():
        return []
    seen = set()
    out: List[str] = []
    for match in _URL_RE.finditer(text):
        raw = canonicalize_media_url(match.group(0))
        parsed = urlparse(raw)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        if raw in seen:
            continue
        seen.add(raw)
        out.append(raw)
    return out
