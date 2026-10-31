"""Single-item download helpers via yt-dlp."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Callable, Optional

from ytscore.adult_tube import rewrite_adult_tube_media_url
from ytscore.backoff import compute_backoff_seconds, is_rate_limited
from ytscore.cache import title_cache
from ytscore.formats import (
    DEFAULT_FORMAT_SORT,
    is_format_unavailable_error,
    next_format_fallback,
    normalize_video_format,
)
from ytscore.resolvers import detect_platform
from ytscore.rule34_video import (
    PLATFORM_ID as RULE34_VIDEO_PLATFORM,
    download_cdn_media,
    extract_page_title,
    fetch_html as rule34_fetch_html,
    rewrite_rule34_video_media_url,
    rule34_video_id,
)
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


DOWNLOAD_ARCHIVE_NAME = ".yts_download_archive.txt"


def download_archive_path(output_dir: str) -> str:
    return os.path.join(output_dir, DOWNLOAD_ARCHIVE_NAME)


def find_existing_by_media_id(output_dir: str, media_id: Optional[str]) -> Optional[str]:
    """Return newest file in ``output_dir`` whose name contains ``[media_id]``."""
    if not media_id or not os.path.isdir(output_dir):
        return None
    needle = f"[{media_id}]"
    found: list[str] = []
    try:
        names = os.listdir(output_dir)
    except OSError:
        return None
    for name in names:
        if needle not in name:
            continue
        full = os.path.join(output_dir, name)
        if os.path.isfile(full):
            found.append(full)
    if not found:
        return None
    found.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return found[0]


def _guess_media_id_from_url(url: str) -> Optional[str]:
    """Best-effort id from common URL shapes (no network)."""
    text = (url or "").strip()
    if not text:
        return None
    lower = text.lower()
    if "youtube.com" in lower or "youtu.be" in lower:
        if "youtu.be/" in lower:
            tail = text.split("youtu.be/", 1)[-1]
            return tail.split("?", 1)[0].split("/", 1)[0].strip() or None
        if "v=" in text:
            return text.split("v=", 1)[-1].split("&", 1)[0].split("#", 1)[0].strip() or None
        if "/shorts/" in lower:
            tail = text.split("/shorts/", 1)[-1]
            return tail.split("?", 1)[0].split("/", 1)[0].strip() or None
    if "viewkey=" in lower:
        return text.split("viewkey=", 1)[-1].split("&", 1)[0].split("#", 1)[0].strip() or None
    r34_id = rule34_video_id(text)
    if r34_id:
        return r34_id
    return None


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
    overwrite = bool(getattr(settings, "overwrite", False))
    skip_existing = bool(getattr(settings, "skip_existing", True)) and not overwrite
    number_files = bool(getattr(settings, "number_files", True))
    use_index = index is not None and number_files
    prefix = f"{index:04d}_" if use_index else ""
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
        active_format = "bestaudio/best"
    else:
        active_format = normalize_video_format(settings.video_format_pref)
        merge_fmt = output_format if output_format in ("mp4", "webm", "mkv") else None
        ydl_opts = {
            "format": active_format,
            "format_sort": list(DEFAULT_FORMAT_SORT),
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "progress_hooks": hooks,
            "merge_output_format": merge_fmt,
        }
        ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}

    if overwrite:
        ydl_opts["overwrites"] = True
    elif skip_existing:
        ydl_opts["nooverwrites"] = True
        ydl_opts["download_archive"] = download_archive_path(output_dir)

    ydl_opts = apply_auth_opts(ydl_opts, settings)
    download_url = url
    if detect_platform(url) == "adult_tube":
        # GIF / photo pages are not handled by yt-dlp extractors; map to CDN media.
        rewritten = rewrite_adult_tube_media_url(url, settings)
        if rewritten and rewritten != url:
            download_url = rewritten
            logging.info("Adult-tube media rewrite %s → %s", url, download_url)
    elif detect_platform(url) == RULE34_VIDEO_PLATFORM:
        # Stock extractor misses formats when the download sheet markup drifts;
        # map video pages to direct get_file CDN URLs (cookies still applied).
        rewritten = rewrite_rule34_video_media_url(url, settings)
        if rewritten and rewritten != url:
            download_url = rewritten
            logging.info("rule34_video media rewrite %s → %s", url, download_url)

    if skip_existing:
        guessed = _guess_media_id_from_url(download_url) or _guess_media_id_from_url(url)
        existing = find_existing_by_media_id(output_dir, guessed)
        if existing:
            title = os.path.basename(existing)
            title_cache.put(url, title)
            logging.info("Skip existing file for %s → %s", url, existing)
            return DownloadResult(ok=True, path=existing, title=title)

    # rule34_video CDN redirects through a .php endpoint yt-dlp refuses to save.
    if (
        detect_platform(url) == RULE34_VIDEO_PLATFORM
        and media == "video"
        and "get_file/" in download_url
    ):
        media_id = rule34_video_id(url) or _guess_media_id_from_url(url) or "video"
        title = ""
        if rule34_video_id(url):
            html, _err = rule34_fetch_html(url, settings)
            title = extract_page_title(html or "")
        title = title or f"rule34_video_{media_id}"
        safe = clean_filename(title) or f"rule34_video_{media_id}"
        dest = os.path.join(output_dir, f"{prefix}{safe} [{media_id}].mp4")
        err = download_cdn_media(
            download_url,
            dest,
            settings,
            referer=url,
            progress_hook=progress_hook,
        )
        if err:
            return DownloadResult(ok=False, error=err)
        title_cache.put(url, title)
        if watermark_path and os.path.isfile(dest):
            from ytscore.watermark import add_watermark

            base, ext = os.path.splitext(dest)
            final = f"{base}_wm{ext if ext else '.mp4'}"
            msg = add_watermark(dest, watermark_path, final)
            if os.path.isfile(final):
                try:
                    os.remove(dest)
                except OSError:
                    pass
                dest = final
            else:
                logging.warning("Watermark step: %s", msg)
        return DownloadResult(ok=True, path=dest, title=title)

    def _finish(info: dict) -> DownloadResult:
        title = (info or {}).get("title") or "unknown_title"
        title_cache.put(url, title)
        media_id = (info or {}).get("id")
        path = _find_download(output_dir, prefix, media_id)
        if path is None and media_id:
            path = find_existing_by_media_id(output_dir, media_id)
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

    last_error = None
    saw_rate_limit = False
    format_fallback_used = False
    attempts = settings.max_retries + 1
    attempt = 0
    while attempt < attempts:
        attempt += 1
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(download_url, download=True)
            return _finish(info)
        except Exception as exc:
            last_error = str(exc)
            limited = is_rate_limited(exc)
            if limited:
                saw_rate_limit = True
            logging.warning("Download attempt %s/%s failed for %s: %s", attempt, attempts, url, exc)
            # Immediate resilient format retry (does not consume a retry/backoff slot).
            if (
                media != "audio"
                and not format_fallback_used
                and is_format_unavailable_error(exc)
            ):
                alt = next_format_fallback(active_format)
                if alt and alt != active_format:
                    logging.info(
                        "Format unavailable; falling back %r → %r for %s",
                        active_format,
                        alt,
                        url,
                    )
                    active_format = alt
                    ydl_opts["format"] = alt
                    format_fallback_used = True
                    attempt -= 1
                    continue
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
