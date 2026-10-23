"""Browser companion handoff: local inbox so the desktop Suite stays the downloader."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ytscore.persist import DEFAULT_STATE_DIR
from ytscore.util import extract_urls

SCHEMA_VERSION = 1
DEFAULT_INBOX_SUBDIR = "inbox"
DEFAULT_INBOX_JSONL = "companion_inbox.jsonl"
PROCESSED_SUFFIX = ".processed"

# Text / JSON drop files the Suite will consume from the inbox directory.
_INBOX_SUFFIXES = (".txt", ".url", ".json", ".jsonl", ".urls")


@dataclass(frozen=True)
class CompanionItem:
    """One media URL handed off from a companion (browser extension or script)."""

    url: str
    title: str = ""
    source: str = ""
    page_url: str = ""


def default_inbox_dir() -> str:
    """Directory where companions drop payload files (under `.ytsdownloader/`)."""
    return os.path.join(DEFAULT_STATE_DIR, DEFAULT_INBOX_SUBDIR)


def default_inbox_jsonl_path() -> str:
    """Append-friendly NDJSON path for streaming companion handoffs."""
    return os.path.join(DEFAULT_STATE_DIR, DEFAULT_INBOX_JSONL)


def ensure_inbox_layout(
    *,
    inbox_dir: Optional[str] = None,
    jsonl_path: Optional[str] = None,
) -> None:
    """Create the companion inbox directory (and parent for the JSONL path)."""
    directory = inbox_dir if inbox_dir is not None else default_inbox_dir()
    os.makedirs(directory, exist_ok=True)
    path = jsonl_path if jsonl_path is not None else default_inbox_jsonl_path()
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)


def _item_from_url(
    url: str,
    *,
    title: str = "",
    source: str = "",
    page_url: str = "",
) -> Optional[CompanionItem]:
    urls = extract_urls(url) if url else []
    if not urls:
        return None
    return CompanionItem(
        url=urls[0],
        title=(title or "").strip(),
        source=(source or "").strip(),
        page_url=(page_url or "").strip(),
    )


def _item_from_mapping(data: Dict[str, Any]) -> Optional[CompanionItem]:
    url = str(data.get("url") or data.get("href") or data.get("media_url") or "")
    title = str(data.get("title") or data.get("name") or "")
    source = str(data.get("source") or data.get("origin") or "")
    page_url = str(data.get("page_url") or data.get("referrer") or "")
    return _item_from_url(url, title=title, source=source, page_url=page_url)


def _items_from_list(values: Sequence[Any]) -> List[CompanionItem]:
    out: List[CompanionItem] = []
    for value in values:
        if isinstance(value, str):
            item = _item_from_url(value)
            if item:
                out.append(item)
        elif isinstance(value, dict):
            item = _item_from_mapping(value)
            if item:
                out.append(item)
    return out


def parse_companion_payload(text: str) -> List[CompanionItem]:
    """
    Parse companion handoff text into unique CompanionItem entries.

    Accepted shapes (in order):
    - NDJSON / JSONL: one JSON object or string URL per line
    - JSON object: ``{"url": "..."}`` or ``{"urls": [...]}`` / ``{"items": [...]}``
    - JSON array of URLs or objects
    - Free text: any http(s) URLs (same rules as paste / drop)
    """
    if not text or not text.strip():
        return []

    stripped = text.strip()
    items: List[CompanionItem] = []

    # Prefer structured JSON when the whole payload is one value.
    if stripped[:1] in ("{", "["):
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            if "url" in data or "href" in data or "media_url" in data:
                item = _item_from_mapping(data)
                if item:
                    return _dedupe([item])
            for key in ("urls", "items", "links"):
                if isinstance(data.get(key), list):
                    return _dedupe(_items_from_list(data[key]))
        elif isinstance(data, list):
            return _dedupe(_items_from_list(data))

    # NDJSON / line-oriented: try JSON per line, else URL extract.
    line_items: List[CompanionItem] = []
    saw_json_line = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line[:1] in ("{", "["):
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                data = None
            if isinstance(data, dict):
                saw_json_line = True
                item = _item_from_mapping(data)
                if item:
                    line_items.append(item)
                continue
            if isinstance(data, list):
                saw_json_line = True
                line_items.extend(_items_from_list(data))
                continue
            if isinstance(data, str):
                saw_json_line = True
                item = _item_from_url(data)
                if item:
                    line_items.append(item)
                continue
        for url in extract_urls(line):
            line_items.append(CompanionItem(url=url))

    if saw_json_line or line_items:
        items = line_items
    else:
        items = [CompanionItem(url=u) for u in extract_urls(text)]

    return _dedupe(items)


def _dedupe(items: Iterable[CompanionItem]) -> List[CompanionItem]:
    seen = set()
    out: List[CompanionItem] = []
    for item in items:
        if not item.url or item.url in seen:
            continue
        seen.add(item.url)
        out.append(item)
    return out


def write_companion_items(
    path: str,
    items: Sequence[CompanionItem],
    *,
    append: bool = True,
) -> None:
    """
    Write companion items as NDJSON (one object per line).

    Used by tests and by external scripts that prefer a single append file.
    """
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as fh:
        for item in items:
            payload = {
                "schema": SCHEMA_VERSION,
                "url": item.url,
                "title": item.title,
                "source": item.source or "script",
                "page_url": item.page_url,
                "ts": time.time(),
            }
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _mark_processed(path: str) -> None:
    """Rename a consumed drop file so companions can detect success."""
    target = path + PROCESSED_SUFFIX
    try:
        if os.path.isfile(target):
            os.remove(target)
        os.replace(path, target)
    except OSError:
        try:
            os.remove(path)
        except OSError:
            pass


def _list_inbox_files(inbox_dir: str) -> List[str]:
    if not inbox_dir or not os.path.isdir(inbox_dir):
        return []
    names = sorted(os.listdir(inbox_dir))
    out: List[str] = []
    for name in names:
        if name.startswith("."):
            continue
        if name.endswith(PROCESSED_SUFFIX):
            continue
        lower = name.lower()
        if not any(lower.endswith(suf) for suf in _INBOX_SUFFIXES):
            continue
        path = os.path.join(inbox_dir, name)
        if os.path.isfile(path):
            out.append(path)
    return out


def consume_companion_inbox(
    *,
    inbox_dir: Optional[str] = None,
    jsonl_path: Optional[str] = None,
) -> List[CompanionItem]:
    """
    Read pending companion payloads, then clear/archive them.

    - Files under ``inbox_dir`` are renamed to ``*.processed`` after a successful read.
    - The append JSONL file (if present and non-empty) is truncated after read.
    """
    directory = inbox_dir if inbox_dir is not None else default_inbox_dir()
    path = jsonl_path if jsonl_path is not None else default_inbox_jsonl_path()
    collected: List[CompanionItem] = []

    for file_path in _list_inbox_files(directory):
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        collected.extend(parse_companion_payload(text))
        _mark_processed(file_path)

    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            text = ""
        if text.strip():
            collected.extend(parse_companion_payload(text))
            try:
                # Truncate after successful parse so partial writes from a
                # companion are not lost mid-poll (companions should append
                # complete lines).
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("")
            except OSError:
                pass

    return _dedupe(collected)
