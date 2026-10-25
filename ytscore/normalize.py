"""Batch URL/path normalize with optional Rust sidecar (Python fallback)."""

from __future__ import annotations

import os
from typing import List, Sequence
from urllib.parse import urlparse

from ytscore.native_bridge import (
    BIN_NORMALIZE,
    find_binary,
    run_json_stdin,
)
from ytscore.util import canonicalize_media_url, extract_urls


def normalize_urls_python(items: Sequence[str]) -> List[str]:
    """Pure-Python URL clean + dedupe (same rules as extract_urls per token)."""
    seen = set()
    out: List[str] = []
    for raw in items:
        if not raw or not str(raw).strip():
            continue
        # Prefer extract_urls so free-text tokens still work.
        found = extract_urls(str(raw))
        if not found:
            candidate = canonicalize_media_url(str(raw))
            parsed = urlparse(candidate)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                found = [candidate]
        for url in found:
            cleaned = canonicalize_media_url(url)
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                out.append(cleaned)
    return out


def normalize_paths_python(items: Sequence[str]) -> List[str]:
    """Pure-Python path normalize + dedupe."""
    seen = set()
    out: List[str] = []
    for raw in items:
        text = str(raw).strip()
        if not text:
            continue
        try:
            path = os.path.abspath(os.path.normpath(text))
        except (OSError, ValueError):
            continue
        if path not in seen:
            seen.add(path)
            out.append(path)
    return out


def normalize_urls(items: Sequence[str]) -> List[str]:
    """
    Normalize and dedupe http(s) URLs.
    Uses Rust ``yts-normalize`` when available; otherwise Python.
    """
    seq = [str(x) for x in items]
    if not seq:
        return []
    binary = find_binary(BIN_NORMALIZE)
    if binary:
        data = run_json_stdin(binary, {"op": "urls", "items": seq})
        if data and data.get("ok") is True and isinstance(data.get("items"), list):
            # Re-validate with Python rules so sidecar quirks cannot widen accept set.
            return normalize_urls_python([str(x) for x in data["items"]])
    return normalize_urls_python(seq)


def normalize_paths(items: Sequence[str]) -> List[str]:
    """Normalize and dedupe filesystem paths (Rust sidecar or Python)."""
    seq = [str(x) for x in items]
    if not seq:
        return []
    binary = find_binary(BIN_NORMALIZE)
    if binary:
        data = run_json_stdin(binary, {"op": "paths", "items": seq})
        if data and data.get("ok") is True and isinstance(data.get("items"), list):
            return normalize_paths_python([str(x) for x in data["items"]])
    return normalize_paths_python(seq)
