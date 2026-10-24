"""On-device yt-dlp helpers for the Android Suite path.

Slice 2: single-file formats (no ffmpeg).
Slice 3: when *ffmpeg_location* is set, prefer bestvideo+bestaudio merge via bundled ffmpeg.
Slice 4: optional full-frame PNG watermark overlay via the same bundled ffmpeg.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

import yt_dlp


# Progressive / single-file only — used when no ffmpeg binary is available.
_FORMAT_SINGLE = "best[height<=720][ext=mp4]/best[ext=mp4]/best[height<=720]/best"
# Separate A/V streams + remux (requires ffmpeg). Cap height to keep on-device work bounded.
_FORMAT_MERGE = (
    "bestvideo[height<=720]+bestaudio/"
    "best[height<=720][ext=mp4]/best[ext=mp4]/best[height<=720]/best"
)

# Full-frame stretch overlay (matches desktop Suite watermark semantics).
# scale2ref stretches the PNG to the video frame; overlay composites at 0,0.
_WM_FILTER = "[1:v][0:v]scale2ref[wm][base];[base][wm]overlay=0:0"


def format_selector(ffmpeg_location: str | None) -> str:
    """Return the yt-dlp format expression for the given ffmpeg availability."""
    if ffmpeg_location and os.path.isfile(ffmpeg_location) and os.access(ffmpeg_location, os.X_OK):
        return _FORMAT_MERGE
    return _FORMAT_SINGLE


def _usable_ffmpeg(ffmpeg_location: str | None) -> str | None:
    ff = (ffmpeg_location or "").strip() or None
    if ff and os.path.isfile(ff) and os.access(ff, os.X_OK):
        return ff
    return None


def _ffmpeg_argv(ff: str, *args: str) -> list[str]:
    """Build an argv that can exec a PIE binary from app files on Android (W^X).

    Direct exec of writable-app-data binaries is blocked for the app zygote; the
    dynamic linker can still load them. Host/desktop just runs *ff* normally.
    """
    linker = "/system/bin/linker64"
    if os.path.isfile(linker) and os.access(linker, os.X_OK):
        return [linker, ff, *args]
    return [ff, *args]


def apply_watermark(
    video_path: str,
    watermark_path: str,
    ffmpeg_location: str,
    output_path: str | None = None,
) -> str:
    """Composite *watermark_path* over *video_path* (full-frame). Returns JSON ok/path/error."""
    if not video_path or not os.path.isfile(video_path):
        return json.dumps({"ok": False, "error": "video missing", "path": ""})
    if not watermark_path or not os.path.isfile(watermark_path):
        return json.dumps({"ok": False, "error": "watermark missing", "path": ""})
    ff = _usable_ffmpeg(ffmpeg_location)
    if not ff:
        return json.dumps({"ok": False, "error": "ffmpeg missing", "path": ""})

    base, ext = os.path.splitext(video_path)
    out = output_path or (base + "_wm.mp4")
    # LGPL Android build: no libx264. mpeg4+aac is reliable with filter_complex;
    # h264_mediacodec often yields empty/undersized output when filters are used.
    # Host tests may have libx264 — try it first when present via a soft probe.
    attempts: list[list[str]] = []
    for vcodec_args in (
        ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"],
        ["-c:v", "mpeg4", "-q:v", "5"],
    ):
        attempts.append(
            _ffmpeg_argv(
                ff,
                "-y",
                "-i",
                video_path,
                "-i",
                watermark_path,
                "-filter_complex",
                _WM_FILTER,
                *vcodec_args,
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                out,
            )
        )
    last_err = "watermark encode failed"
    min_bytes = max(2000, int(os.path.getsize(video_path) * 0.05))
    for cmd in attempts:
        try:
            if os.path.isfile(out):
                try:
                    os.remove(out)
                except OSError:
                    pass
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
            if proc.returncode == 0 and os.path.isfile(out) and os.path.getsize(out) >= min_bytes:
                if os.path.abspath(out) != os.path.abspath(video_path):
                    try:
                        os.remove(video_path)
                    except OSError:
                        pass
                return json.dumps({"ok": True, "path": out, "error": ""})
            err = (proc.stderr or proc.stdout or "").strip()
            last_err = err[-500:] if err else f"ffmpeg exit {proc.returncode}"
        except subprocess.TimeoutExpired:
            last_err = "watermark timed out"
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
    return json.dumps({"ok": False, "error": last_err, "path": ""})


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


def download(
    url: str,
    out_dir: str,
    callback=None,
    ffmpeg_location: str | None = None,
    watermark_path: str | None = None,
) -> str:
    """Download *url* into *out_dir*. Returns JSON: ok/path/title/error/merged/watermarked."""
    os.makedirs(out_dir, exist_ok=True)
    outtmpl = os.path.join(out_dir, "%(title).80B [%(id)s].%(ext)s")
    hooks = []
    if callback is not None:
        hooks.append(lambda d: _progress_hook(callback, d))

    ff = _usable_ffmpeg(ffmpeg_location)
    fmt = format_selector(ff)
    merged = fmt == _FORMAT_MERGE
    watermarked = False

    opts: dict[str, Any] = {
        "format": fmt,
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
    if merged and ff:
        opts["ffmpeg_location"] = ff
        opts["merge_output_format"] = "mp4"

    info: dict[str, Any] | None = None
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                return json.dumps(
                    {"ok": False, "error": "no info", "merged": merged, "watermarked": False}
                )
            path = ydl.prepare_filename(info)
            # prepare_filename may use the template before remux; prefer requested downloads.
            requested = info.get("requested_downloads") or []
            if requested:
                cand = requested[0].get("filepath") or requested[0].get("_filename")
                if cand:
                    path = cand
            # After merge, extension is often forced to mp4 regardless of template.
            if path and not os.path.isfile(path):
                base, _ext = os.path.splitext(path)
                for cand_ext in (".mp4", ".mkv", ".webm", ".m4a"):
                    alt = base + cand_ext
                    if os.path.isfile(alt):
                        path = alt
                        break
            if not path or not os.path.isfile(path):
                # Fallback: newest file in out_dir (skip partials).
                files = [
                    os.path.join(out_dir, name)
                    for name in os.listdir(out_dir)
                    if os.path.isfile(os.path.join(out_dir, name))
                    and not name.endswith(".part")
                    and not name.endswith(".ytdl")
                ]
                if not files:
                    return json.dumps(
                        {
                            "ok": False,
                            "error": "download finished but file missing",
                            "merged": merged,
                            "watermarked": False,
                        }
                    )
                path = max(files, key=os.path.getmtime)
            title = (info.get("title") or "").strip()
            wm = (watermark_path or "").strip() or None
            if wm and ff:
                raw_wm = apply_watermark(path, wm, ff)
                wm_payload = json.loads(raw_wm)
                if wm_payload.get("ok") and wm_payload.get("path"):
                    path = wm_payload["path"]
                    watermarked = True
                else:
                    return json.dumps(
                        {
                            "ok": False,
                            "error": f"watermark failed: {wm_payload.get('error') or 'unknown'}",
                            "merged": merged,
                            "watermarked": False,
                            "path": path,
                            "title": title,
                        }
                    )
            return json.dumps(
                {
                    "ok": True,
                    "path": path,
                    "title": title,
                    "merged": merged,
                    "watermarked": watermarked,
                }
            )
    except Exception as exc:  # noqa: BLE001 — surface to Kotlin UI
        return json.dumps(
            {"ok": False, "error": str(exc), "merged": merged, "watermarked": watermarked}
        )


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
