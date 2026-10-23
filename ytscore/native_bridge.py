"""Discover and invoke optional native sidecars (fail soft → Python fallback)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence

# Binary names produced by scripts/build_natives.sh into native/bin/
BIN_NORMALIZE = "yts-normalize"
BIN_PRIO = "yts-prio"
BIN_INBOX = "yts-inbox"
RUBY_FILTER = "yts_json_filter.rb"

_DEFAULT_TIMEOUT = 30.0


def native_bin_dir() -> str:
    """Directory for built sidecars (override with YTS_NATIVE_DIR)."""
    override = os.environ.get("YTS_NATIVE_DIR", "").strip()
    if override:
        return os.path.abspath(override)
    # Prefer repo-relative native/bin when running from a checkout.
    here = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "native", "bin"))
    return here


def natives_enabled() -> bool:
    """YTS_USE_NATIVE=0 disables all native helpers."""
    flag = os.environ.get("YTS_USE_NATIVE", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


@lru_cache(maxsize=8)
def find_binary(name: str) -> Optional[str]:
    """Return absolute path to a sidecar binary, or None if missing."""
    if not natives_enabled():
        return None
    local = os.path.join(native_bin_dir(), name)
    if os.path.isfile(local) and os.access(local, os.X_OK):
        return local
    found = shutil.which(name)
    if found and os.access(found, os.X_OK):
        return found
    return None


@lru_cache(maxsize=2)
def find_ruby_filter() -> Optional[str]:
    """Return path to the Ruby JSON filter script, or None."""
    if not natives_enabled():
        return None
    ruby = shutil.which("ruby")
    if not ruby:
        return None
    candidates = [
        os.path.join(native_bin_dir(), RUBY_FILTER),
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "native", "ruby", RUBY_FILTER)
        ),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def clear_native_cache() -> None:
    """Drop cached discovery results (tests / after build)."""
    find_binary.cache_clear()
    find_ruby_filter.cache_clear()


def run_json_stdin(
    binary: str,
    payload: Dict[str, Any],
    *,
    timeout: float = _DEFAULT_TIMEOUT,
    extra_args: Optional[Sequence[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Run a sidecar with JSON on stdin; parse one JSON object from stdout.
    Returns None on any failure (caller must fall back).
    """
    try:
        raw_in = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        args = [binary]
        if extra_args:
            args.extend(extra_args)
        proc = subprocess.run(
            args,
            input=raw_in,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0:
            return None
        text = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
        if not text:
            return None
        # First JSON object line (sidecars print one object).
        line = text.splitlines()[0]
        data = json.loads(line)
        if not isinstance(data, dict):
            return None
        return data
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return None


def run_argv_json(
    binary: str,
    argv: Sequence[str],
    *,
    timeout: float = _DEFAULT_TIMEOUT,
) -> Optional[Dict[str, Any]]:
    """Run binary with argv; parse first JSON object line from stdout."""
    try:
        proc = subprocess.run(
            [binary, *argv],
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0:
            return None
        text = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
        if not text:
            return None
        data = json.loads(text.splitlines()[0])
        return data if isinstance(data, dict) else None
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return None


def run_ndjson_argv(
    binary: str,
    argv: Sequence[str],
    *,
    timeout: float = _DEFAULT_TIMEOUT,
) -> Optional[List[Dict[str, Any]]]:
    """Run binary; parse stdout as NDJSON objects. None on failure."""
    try:
        proc = subprocess.run(
            [binary, *argv],
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0:
            return None
        text = (proc.stdout or b"").decode("utf-8", errors="replace")
        items: List[Dict[str, Any]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                return None
            if isinstance(obj, dict):
                items.append(obj)
        return items
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def run_ruby_filter(text: str, *, timeout: float = _DEFAULT_TIMEOUT) -> Optional[List[Dict[str, Any]]]:
    """Pipe text through the Ruby companion JSON filter. None on failure."""
    script = find_ruby_filter()
    ruby = shutil.which("ruby")
    if not script or not ruby:
        return None
    try:
        proc = subprocess.run(
            [ruby, script],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0:
            return None
        out = (proc.stdout or b"").decode("utf-8", errors="replace")
        items: List[Dict[str, Any]] = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                items.append(obj)
        return items
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return None


def native_status() -> Dict[str, Any]:
    """Diagnostic snapshot for Settings / docs / tests."""
    return {
        "enabled": natives_enabled(),
        "bin_dir": native_bin_dir(),
        "normalize": find_binary(BIN_NORMALIZE),
        "prio": find_binary(BIN_PRIO),
        "inbox": find_binary(BIN_INBOX),
        "ruby_filter": find_ruby_filter(),
    }
