"""On-device yt-dlp helpers for the Android Suite path.

Slice 2: single-file formats (no ffmpeg).
Slice 3: when *ffmpeg_location* is set, prefer bestvideo+bestaudio merge via bundled ffmpeg.
Slice 4: optional full-frame PNG watermark overlay via the same bundled ffmpeg.
Slice 5 (v0.12): export presets (audio_only / video_audio / watermark), optional Netscape
cookiefile (SAF / browser export — no Play Services), concurrent downloads bounded in Kotlin.
Slice 6 (v0.14): outer retry / exponential backoff for transient mobile CDN failures
(Errno 104, SSL, 429/5xx) on top of yt-dlp fragment retries.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from typing import Any

import yt_dlp


# Progressive / single-file only — used when no ffmpeg binary is available.
_FORMAT_SINGLE = "best[height<=720][ext=mp4]/best[ext=mp4]/best[height<=720]/best"
# Separate A/V streams + remux (requires ffmpeg). Cap height to keep on-device work bounded.
# bestvideo* tolerates incomplete codec metadata; progressive best* is the last resort.
_FORMAT_MERGE = (
    "bestvideo*[height<=720]+bestaudio/"
    "bestvideo[height<=720]+bestaudio/"
    "best[height<=720][ext=mp4]/best[ext=mp4]/best[height<=720]/best"
)
# On-device: reuse progressive single-file selection (DASH bestaudio often hits
# Errno 104 on phone networks). Strip to audio after download via ffmpeg.
_FORMAT_AUDIO = _FORMAT_SINGLE

# Full-frame stretch overlay (matches desktop Suite watermark semantics).
# scale2ref stretches the PNG to the video frame; overlay composites at 0,0.
_WM_FILTER = "[1:v][0:v]scale2ref[wm][base];[base][wm]overlay=0:0"

_VALID_PRESETS = frozenset({"audio_only", "video_audio", "watermark"})


def resolve_preset(preset: str | None) -> dict[str, Any]:
    """Map a preset id to media / container / watermark flags (desktop Suite parity)."""
    key = (preset or "video_audio").strip().lower() or "video_audio"
    if key not in _VALID_PRESETS:
        key = "video_audio"
    if key == "audio_only":
        return {
            "preset": "audio_only",
            "media": "audio",
            "output_format": "m4a",
            "use_watermark": False,
        }
    if key == "watermark":
        return {
            "preset": "watermark",
            "media": "video",
            "output_format": "mp4",
            "use_watermark": True,
        }
    return {
        "preset": "video_audio",
        "media": "video",
        "output_format": "mp4",
        "use_watermark": False,
    }


def format_selector(
    ffmpeg_location: str | None,
    *,
    media: str = "video",
) -> str:
    """Return the yt-dlp format expression for media type + ffmpeg availability."""
    if (media or "video").strip().lower() == "audio":
        return _FORMAT_AUDIO
    if ffmpeg_location and os.path.isfile(ffmpeg_location) and os.access(ffmpeg_location, os.X_OK):
        return _FORMAT_MERGE
    return _FORMAT_SINGLE


def _usable_ffmpeg(ffmpeg_location: str | None) -> str | None:
    ff = (ffmpeg_location or "").strip() or None
    if ff and os.path.isfile(ff) and os.access(ff, os.X_OK):
        return ff
    return None


def _usable_cookiefile(cookiefile: str | None) -> str | None:
    path = (cookiefile or "").strip() or None
    if path and os.path.isfile(path) and os.path.getsize(path) > 0:
        return path
    return None


# Outer download attempts beyond yt-dlp's own fragment retries (mobile CDN flakes).
_MAX_OUTER_ATTEMPTS = 3
_BACKOFF_BASE = 2.0
_BACKOFF_FACTOR = 2.0
_BACKOFF_MAX = 45.0

_RETRYABLE_RE = re.compile(
    r"(?i)(?:"
    r"\b429\b|"
    r"too many requests|"
    r"rate[-\s]?limit|"
    r"http error 429|"
    r"\b503\b|"
    r"\b502\b|"
    r"\b500\b|"
    r"timed? ?out|"
    r"timeout|"
    r"connection (?:reset|aborted|refused)|"
    r"errno 104|"
    r"broken pipe|"
    r"ssl|"
    r"temporarily unavailable|"
    r"unable to download"
    r")"
)
_HARD_RATE_RE = re.compile(
    r"(?i)(?:\b429\b|too many requests|rate[-\s]?limit|http error 429|slow down)"
)


def is_retryable_temporary(error: Any) -> bool:
    """True for transient CDN / rate-limit failures worth an outer retry."""
    text = error if isinstance(error, str) else f"{type(error).__name__}: {error}"
    return bool(_RETRYABLE_RE.search(text or ""))


def is_rate_limited(error: Any) -> bool:
    text = error if isinstance(error, str) else f"{type(error).__name__}: {error}"
    return bool(_HARD_RATE_RE.search(text or ""))


def compute_backoff_seconds(
    attempt: int,
    *,
    base: float = _BACKOFF_BASE,
    factor: float = _BACKOFF_FACTOR,
    maximum: float = _BACKOFF_MAX,
    rate_limited: bool = False,
) -> float:
    """Exponential backoff for outer attempt ``attempt`` (1 = first retry after failure)."""
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


def _maybe_remux_audio(path: str, ffmpeg_location: str, preferred: str = "m4a") -> str | None:
    """If *path* is not already a common audio file, remux/extract via linker-safe ffmpeg."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in ("m4a", "aac", "mp3", "opus", "ogg", "flac", "wav"):
        return path
    ff = _usable_ffmpeg(ffmpeg_location)
    if not ff:
        return path
    codec = (preferred or "m4a").strip().lower() or "m4a"
    out = os.path.splitext(path)[0] + f".{codec}"
    # -vn drop video if a low-res video fallback was selected; copy audio when possible.
    cmd = _ffmpeg_argv(
        ff,
        "-y",
        "-i",
        path,
        "-vn",
        "-c:a",
        "copy" if codec in ("m4a", "aac", "opus", "ogg") else "aac",
        out,
    )
    if codec == "mp3":
        cmd = _ffmpeg_argv(ff, "-y", "-i", path, "-vn", "-c:a", "libmp3lame", "-q:a", "4", out)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
        if proc.returncode == 0 and os.path.isfile(out) and os.path.getsize(out) > 200:
            if os.path.abspath(out) != os.path.abspath(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
            return out
        # Retry with re-encode if stream copy failed.
        cmd2 = _ffmpeg_argv(ff, "-y", "-i", path, "-vn", "-c:a", "aac", "-b:a", "192k", out)
        proc2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=300, check=False)
        if proc2.returncode == 0 and os.path.isfile(out) and os.path.getsize(out) > 200:
            if os.path.abspath(out) != os.path.abspath(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
            return out
    except Exception:  # noqa: BLE001
        return path
    return path


def _resolve_downloaded_path(ydl: yt_dlp.YoutubeDL, info: dict[str, Any], out_dir: str) -> str | None:
    path = ydl.prepare_filename(info)
    requested = info.get("requested_downloads") or []
    if requested:
        cand = requested[0].get("filepath") or requested[0].get("_filename")
        if cand:
            path = cand
    if path and not os.path.isfile(path):
        base, _ext = os.path.splitext(path)
        for cand_ext in (".mp4", ".mkv", ".webm", ".m4a", ".opus", ".mp3"):
            alt = base + cand_ext
            if os.path.isfile(alt):
                path = alt
                break
    if path and os.path.isfile(path):
        return path
    files = [
        os.path.join(out_dir, name)
        for name in os.listdir(out_dir)
        if os.path.isfile(os.path.join(out_dir, name))
        and not name.endswith(".part")
        and not name.endswith(".ytdl")
    ]
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def download(
    url: str,
    out_dir: str,
    callback=None,
    ffmpeg_location: str | None = None,
    watermark_path: str | None = None,
    cookiefile: str | None = None,
    preset: str | None = None,
) -> str:
    """Download *url* into *out_dir*.

    Returns JSON: ok/path/title/error/merged/watermarked/preset/media.
    Empty strings for optional paths are treated as unset (Chaquopy positional args).
    """
    os.makedirs(out_dir, exist_ok=True)
    outtmpl = os.path.join(out_dir, "%(title).80B [%(id)s].%(ext)s")
    hooks = []
    if callback is not None:
        hooks.append(lambda d: _progress_hook(callback, d))

    resolved = resolve_preset(preset)
    media = resolved["media"]
    use_wm = bool(resolved["use_watermark"])
    ff = _usable_ffmpeg(ffmpeg_location)
    cookies = _usable_cookiefile(cookiefile)
    fmt = format_selector(ff, media=media)
    merged = media == "video" and fmt == _FORMAT_MERGE
    watermarked = False

    opts: dict[str, Any] = {
        "format": fmt,
        "outtmpl": outtmpl,
        "noprogress": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "retries": 5,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": 1,
        "progress_hooks": hooks,
        # Avoid needing external JS runtimes on device for this slice.
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }
    if cookies:
        opts["cookiefile"] = cookies
    if media == "audio":
        # Prefer progressive download; remux/strip after download via linker-safe ffmpeg.
        if ff:
            opts["ffmpeg_location"] = ff
        # If the selected format is a low progressive mp4 fallback, still ok —
        # _maybe_remux_audio will -vn extract.
    elif merged and ff:
        opts["ffmpeg_location"] = ff
        opts["merge_output_format"] = "mp4"

    last_err = "unknown error"
    for attempt in range(1, _MAX_OUTER_ATTEMPTS + 1):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    last_err = "no info"
                    if attempt < _MAX_OUTER_ATTEMPTS:
                        time.sleep(compute_backoff_seconds(attempt))
                        continue
                    return json.dumps(
                        {
                            "ok": False,
                            "error": last_err,
                            "merged": merged,
                            "watermarked": False,
                            "preset": resolved["preset"],
                            "media": media,
                            "attempts": attempt,
                        }
                    )
                path = _resolve_downloaded_path(ydl, info, out_dir)
                if not path:
                    last_err = "download finished but file missing"
                    if attempt < _MAX_OUTER_ATTEMPTS and is_retryable_temporary(last_err):
                        time.sleep(compute_backoff_seconds(attempt))
                        continue
                    return json.dumps(
                        {
                            "ok": False,
                            "error": last_err,
                            "merged": merged,
                            "watermarked": False,
                            "preset": resolved["preset"],
                            "media": media,
                            "attempts": attempt,
                        }
                    )
                title = (info.get("title") or "").strip()
                if media == "audio" and ff and path:
                    path = _maybe_remux_audio(path, ff, resolved["output_format"] or "m4a") or path
                wm = (watermark_path or "").strip() or None
                if use_wm and wm and ff and media == "video":
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
                                "preset": resolved["preset"],
                                "media": media,
                                "attempts": attempt,
                            }
                        )
                return json.dumps(
                    {
                        "ok": True,
                        "path": path,
                        "title": title,
                        "merged": merged,
                        "watermarked": watermarked,
                        "preset": resolved["preset"],
                        "media": media,
                        "attempts": attempt,
                    }
                )
        except Exception as exc:  # noqa: BLE001 — surface to Kotlin UI after retries
            last_err = str(exc)
            if attempt < _MAX_OUTER_ATTEMPTS and is_retryable_temporary(exc):
                delay = compute_backoff_seconds(
                    attempt,
                    rate_limited=is_rate_limited(exc),
                )
                time.sleep(delay)
                continue
            return json.dumps(
                {
                    "ok": False,
                    "error": last_err,
                    "merged": merged,
                    "watermarked": watermarked,
                    "preset": resolved["preset"],
                    "media": media,
                    "attempts": attempt,
                }
            )
    return json.dumps(
        {
            "ok": False,
            "error": last_err,
            "merged": merged,
            "watermarked": watermarked,
            "preset": resolved["preset"],
            "media": media,
            "attempts": _MAX_OUTER_ATTEMPTS,
        }
    )


def resolve_title(url: str, cookiefile: str | None = None) -> str:
    """Optional yt-dlp title resolve (richer than oEmbed; may be slower)."""
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }
    cookies = _usable_cookiefile(cookiefile)
    if cookies:
        opts["cookiefile"] = cookies
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return ""
            return str(info.get("title") or "").strip()
    except Exception:  # noqa: BLE001
        return ""
