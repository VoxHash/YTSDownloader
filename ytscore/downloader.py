"""Single-item download helpers via yt-dlp."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Callable, Optional

from ytscore.backoff import compute_backoff_seconds, is_rate_limited
from ytscore.cache import title_cache
from ytscore.settings import Settings, apply_auth_opts
from ytscore.util import clean_filename

try:
    import yt_dlp
except ImportError:  # pragma: no cover
    yt_dlp = None


ProgressCb = Optional[Callable[[dict], None]]


@dataclass
class DownloadResult:
    ok: bool
    path: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None
    rate_limited: bool = False


def _require_yt_dlp():
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed")
    return yt_dlp


def fetch_title(url: str, settings: Settings) -> str:
    cached = title_cache.get(url)
    if cached:
        return cached
    # get() already counted a miss; undo miss then put correctly via extract
    title_cache.misses = max(0, title_cache.misses - 1)
    yt_dlp = _require_yt_dlp()
    ydl_opts = apply_auth_opts({"quiet": True, "skip_download": True}, settings)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    title = (info or {}).get("title") or "unknown_title"
    title_cache.put(url, title)
    return title


def download_item(
    url: str,
    output_dir: str,
    settings: Settings,
    *,
    media: str = "video",
    index: Optional[int] = None,
    watermark_path: str = "",
    output_format: str = "mp4",
    progress_hook: ProgressCb = None,
) -> DownloadResult:
    """Download one URL. media: 'video' | 'audio'."""
    yt_dlp = _require_yt_dlp()
    os.makedirs(output_dir, exist_ok=True)
    prefix = f"{index:04d}_" if index is not None else ""
    outtmpl = os.path.join(output_dir, f"{prefix}%(title).180B [%(id)s].%(ext)s")

    hooks = []
    if progress_hook:
        hooks.append(progress_hook)

    if media == "audio":
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "progress_hooks": hooks,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": settings.audio_format,
                    "preferredquality": "192",
                }
            ],
        }
    else:
        ydl_opts = {
            "format": settings.video_format_pref,
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "progress_hooks": hooks,
            "merge_output_format": output_format if output_format in ("mp4", "webm", "mkv") else None,
        }
        ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}

    ydl_opts = apply_auth_opts(ydl_opts, settings)
    last_error = None
    saw_rate_limit = False
    attempts = settings.max_retries + 1
    for attempt in range(1, attempts + 1):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            title = (info or {}).get("title") or "unknown_title"
            title_cache.put(url, title)
            # Locate newest matching file
            path = _find_download(output_dir, prefix, (info or {}).get("id"))
            if watermark_path and path and media == "video":
                from ytscore.watermark import add_watermark

                base, ext = os.path.splitext(path)
                final = f"{base}_wm{ext if ext else '.' + output_format}"
                msg = add_watermark(path, watermark_path, final)
                if os.path.isfile(final):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                    path = final
                else:
                    logging.warning("Watermark step: %s", msg)
            return DownloadResult(ok=True, path=path, title=title)
        except Exception as exc:
            last_error = str(exc)
            limited = is_rate_limited(exc)
            if limited:
                saw_rate_limit = True
            logging.warning("Download attempt %s/%s failed for %s: %s", attempt, attempts, url, exc)
            if attempt >= attempts:
                break
            # Exponential wait; HTTP 429 / rate-limit signals use a harder base.
            delay = compute_backoff_seconds(
                attempt,
                base=settings.backoff_base,
                factor=settings.backoff_factor,
                maximum=settings.backoff_max,
                rate_limited=limited,
            )
            logging.info(
                "Backoff %.1fs before retry %s/%s (rate_limited=%s)",
                delay,
                attempt + 1,
                attempts,
                limited,
            )
            if delay > 0:
                time.sleep(delay)
    return DownloadResult(
        ok=False,
        error=last_error or "unknown error",
        rate_limited=saw_rate_limit or is_rate_limited(last_error),
    )


def search_and_download_audio(
    query: str,
    output_dir: str,
    settings: Settings,
    *,
    progress_hook: ProgressCb = None,
) -> DownloadResult:
    """Resolve first search hit then download as audio."""
    search_url = f"ytsearch1:{query}"
    return download_item(
        search_url,
        output_dir,
        settings,
        media="audio",
        progress_hook=progress_hook,
    )


def _find_download(output_dir: str, prefix: str, media_id: Optional[str]) -> Optional[str]:
    def collect(*, require_id: bool) -> list:
        found = []
        for name in os.listdir(output_dir):
            if prefix and not name.startswith(prefix):
                continue
            if require_id and media_id and media_id not in name:
                continue
            full = os.path.join(output_dir, name)
            if os.path.isfile(full):
                found.append(full)
        return found

    candidates = collect(require_id=True) if media_id else collect(require_id=False)
    if not candidates and media_id:
        candidates = collect(require_id=False)
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def write_name_map(links: list, output_path: str, output_format: str, settings: Settings) -> None:
    path = os.path.join(output_path, "original_names.txt")
    with open(path, "w", encoding="utf-8") as file:
        for link in links:
            try:
                title = fetch_title(link, settings)
            except Exception as error:
                logging.warning("Could not fetch metadata for %s: %s", link, error)
                title = "unknown_title"
            file.write(f"{link}|{clean_filename(title)}.{output_format}\n")
