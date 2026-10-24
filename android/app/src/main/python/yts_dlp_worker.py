"""On-device yt-dlp helpers for the Android Suite path (slice 2).

Single-file formats only — no ffmpeg merge / watermark in this slice.
"""

from __future__ import annotations

import json
import os
from typing import Any

import yt_dlp


# Progressive / single-file only — no ffmpeg merge in this slice.
_FORMAT = "best[height<=720][ext=mp4]/best[ext=mp4]/best[height<=720]/best"


def _progress_hook(callback, d: dict[str, Any]) -> None:
    if callback is None:
        return
    status = d.get("status")
    if status == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        done = d.get("downloaded_bytes") or 0
        pct = 0.0
        if total:
            pct = max(0.0, min(100.0, (float(done) / float(total)) * 100.0))
        elif d.get("_percent_str"):
            raw = str(d["_percent_str"]).replace("%", "").strip()
            try:
                pct = float(raw)
            except ValueError:
                pct = 0.0
        callback.on_progress(float(pct), str(d.get("_eta_str") or ""))
    elif status == "finished":
        callback.on_progress(100.0, "0")


def download(url: str, out_dir: str, callback=None) -> str:
    """Download *url* into *out_dir*. Returns JSON: ok/path/title/error."""
    os.makedirs(out_dir, exist_ok=True)
    outtmpl = os.path.join(out_dir, "%(title).80B [%(id)s].%(ext)s")
    hooks = []
    if callback is not None:
        hooks.append(lambda d: _progress_hook(callback, d))

    opts = {
        "format": _FORMAT,
        "outtmpl": outtmpl,
        "noprogress": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 3,
        "concurrent_fragment_downloads": 1,
        "progress_hooks": hooks,
        # Avoid needing external JS runtimes on device for this slice.
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }

    info: dict[str, Any] | None = None
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                return json.dumps({"ok": False, "error": "no info"})
            path = ydl.prepare_filename(info)
            # prepare_filename may use the template before remux; prefer requested downloads.
            requested = info.get("requested_downloads") or []
            if requested:
                cand = requested[0].get("filepath") or requested[0].get("_filename")
                if cand:
                    path = cand
            if not path or not os.path.isfile(path):
                # Fallback: newest file in out_dir
                files = [
                    os.path.join(out_dir, name)
                    for name in os.listdir(out_dir)
                    if os.path.isfile(os.path.join(out_dir, name))
                ]
                if not files:
                    return json.dumps({"ok": False, "error": "download finished but file missing"})
                path = max(files, key=os.path.getmtime)
            title = (info.get("title") or "").strip()
            return json.dumps({"ok": True, "path": path, "title": title})
    except Exception as exc:  # noqa: BLE001 — surface to Kotlin UI
        return json.dumps({"ok": False, "error": str(exc)})


def resolve_title(url: str) -> str:
    """Optional yt-dlp title resolve (richer than oEmbed; may be slower)."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return ""
            return str(info.get("title") or "").strip()
    except Exception:  # noqa: BLE001
        return ""
