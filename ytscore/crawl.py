"""Profile / channel crawl modes behind cookie auth (legally constrained surfaces).

Deep modes enumerate items the user can already reach with the configured
extractor + local cookies (browser profile or cookie file). They do not bypass
paywalls, DRM, or private surfaces the signed-in session cannot access.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional, Sequence

from ytscore.backoff import compute_backoff_seconds, is_rate_limited
from ytscore.cache import title_cache
from ytscore.resolvers import detect_platform, resolve_flat, resolve_url
from ytscore.settings import Settings, apply_auth_opts

try:
    import yt_dlp
except ImportError:  # pragma: no cover
    yt_dlp = None

SleepFn = Callable[[float], None]


class CrawlMode(str, Enum):
    """How aggressively to expand a profile / channel URL into item links."""

    SHALLOW = "shallow"
    DEEP = "deep"
    VIDEOS = "videos"
    SHORTS = "shorts"
    POSTS = "posts"


# Human labels for Suite combo boxes (id → label).
CRAWL_MODE_LABELS = {
    CrawlMode.SHALLOW: "Shallow (single pass)",
    CrawlMode.DEEP: "Deep (multi-tab, cookie auth)",
    CrawlMode.VIDEOS: "Videos tab / feed (cookie auth)",
    CrawlMode.SHORTS: "Shorts / clips (cookie auth)",
    CrawlMode.POSTS: "Posts / reels (cookie auth)",
}


class CrawlAuthError(RuntimeError):
    """Raised when a deep crawl mode is requested without cookie auth configured."""


@dataclass
class CrawlResult:
    urls: List[str] = field(default_factory=list)
    mode: CrawlMode = CrawlMode.SHALLOW
    platform: str = "generic"
    tabs_tried: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    auth_required: bool = False
    auth_configured: bool = False


def cookie_auth_configured(settings: Settings) -> bool:
    """True when COOKIES_FROM_BROWSER or COOKIES_FILE is set."""
    if settings.cookies_tuple():
        return True
    return bool((settings.cookies_file or "").strip())


def crawl_requires_auth(mode: CrawlMode) -> bool:
    """Deep / tab-specific modes only run when cookie auth is configured."""
    return mode != CrawlMode.SHALLOW


def parse_crawl_mode(value: str | CrawlMode | None) -> CrawlMode:
    if isinstance(value, CrawlMode):
        return value
    text = (value or "").strip().lower()
    if not text:
        return CrawlMode.SHALLOW
    try:
        return CrawlMode(text)
    except ValueError as exc:
        raise ValueError(f"Unknown crawl mode: {value!r}") from exc


def clamp_crawl_limit(limit: int, *, default: int = 50, maximum: int = 500) -> int:
    try:
        n = int(limit)
    except (TypeError, ValueError):
        n = default
    if n < 1:
        n = 1
    if maximum > 0 and n > maximum:
        n = maximum
    return n


def _require_yt_dlp():
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed")
    return yt_dlp


def _youtube_channel_root(url: str) -> str:
    channel_url = url.strip()
    for part in (
        "/about",
        "/community",
        "/playlist",
        "/playlists",
        "/streams",
        "/featured",
        "/videos",
        "/shorts",
        "/live",
    ):
        channel_url = channel_url.split(part)[0]
    return channel_url.rstrip("/")


def _is_youtube_single(url: str) -> bool:
    u = url.strip()
    return "/watch?" in u or "/shorts/" in u or "youtu.be/" in u


def _youtube_tabs_for_mode(mode: CrawlMode) -> List[str]:
    if mode == CrawlMode.VIDEOS:
        return ["/videos"]
    if mode == CrawlMode.SHORTS:
        return ["/shorts"]
    if mode == CrawlMode.POSTS:
        return ["/videos", "/shorts"]
    if mode == CrawlMode.DEEP:
        return ["/videos", "/shorts", "/streams"]
    return ["/videos", "/shorts"]


def _entries_to_urls(entries: Sequence[object], *, limit: int) -> List[str]:
    links: List[str] = []
    for entry in entries or []:
        if len(links) >= limit:
            break
        if not entry or not isinstance(entry, dict):
            continue
        entry_url = entry.get("url") or entry.get("webpage_url")
        entry_id = entry.get("id")
        entry_title = entry.get("title")
        if entry_url and str(entry_url).startswith("http"):
            links.append(str(entry_url))
            title_cache.put(str(entry_url), entry_title)
        elif entry_id:
            resolved = f"https://www.youtube.com/watch?v={entry_id}"
            links.append(resolved)
            title_cache.put(resolved, entry_title)
    return links


def _extract_flat_paged(
    url: str,
    settings: Settings,
    *,
    playlist_end: int,
) -> tuple[List[str], Optional[str]]:
    """Return (urls, error_message)."""
    ydl = _require_yt_dlp()
    ydl_opts = apply_auth_opts(
        {
            "quiet": True,
            "extract_flat": True,
            "skip_download": True,
            "playlist_end": playlist_end,
        },
        settings,
    )
    try:
        with ydl.YoutubeDL(ydl_opts) as client:
            result = client.extract_info(url, download=False)
    except Exception as error:
        return [], str(error)

    if not isinstance(result, dict):
        return [], "unexpected extractor payload"
    entries = result.get("entries")
    if entries:
        return _entries_to_urls(list(entries), limit=playlist_end), None
    # Single item
    page = result.get("webpage_url") or result.get("url") or url
    title = result.get("title")
    if page and str(page).startswith("http"):
        title_cache.put(str(page), title)
        return [str(page)], None
    return [url], None


def _paced_sleep(
    seconds: float,
    *,
    sleep_fn: SleepFn,
    attempt: int = 1,
    rate_limited: bool = False,
    settings: Optional[Settings] = None,
) -> None:
    delay = max(0.0, float(seconds))
    if rate_limited and settings is not None:
        delay = max(
            delay,
            compute_backoff_seconds(
                attempt,
                base=settings.backoff_base,
                factor=settings.backoff_factor,
                maximum=settings.backoff_max,
                rate_limited=True,
            ),
        )
    if delay > 0:
        sleep_fn(delay)


def crawl_youtube(
    url: str,
    settings: Settings,
    *,
    mode: CrawlMode,
    limit: int,
    pace_seconds: float,
    sleep_fn: SleepFn = time.sleep,
) -> CrawlResult:
    platform = "youtube"
    result = CrawlResult(
        mode=mode,
        platform=platform,
        auth_required=crawl_requires_auth(mode),
        auth_configured=cookie_auth_configured(settings),
    )
    input_url = url.strip()
    if _is_youtube_single(input_url):
        result.urls = [input_url]
        return result

    if mode == CrawlMode.SHALLOW:
        result.urls = resolve_url(input_url, settings, playlist_end=limit)
        return result

    root = _youtube_channel_root(input_url)
    tabs = _youtube_tabs_for_mode(mode)
    seen: dict[str, None] = {}
    attempt = 0
    for i, tab in enumerate(tabs):
        if len(seen) >= limit:
            break
        tab_url = f"{root}{tab}"
        result.tabs_tried.append(tab)
        if i > 0:
            _paced_sleep(pace_seconds, sleep_fn=sleep_fn, settings=settings)
        remaining = limit - len(seen)
        urls, err = _extract_flat_paged(
            tab_url, settings, playlist_end=remaining
        )
        if err:
            result.errors.append(f"{tab}: {err}")
            logging.warning("Crawl tab failed %s: %s", tab_url, err)
            attempt += 1
            _paced_sleep(
                pace_seconds,
                sleep_fn=sleep_fn,
                attempt=attempt,
                rate_limited=is_rate_limited(err),
                settings=settings,
            )
            continue
        for u in urls:
            if u not in seen:
                seen[u] = None
            if len(seen) >= limit:
                break

    if not seen:
        # Fallback: treat as playlist / channel flat extract
        fallback = resolve_flat(input_url, settings, playlist_end=limit)
        for u in fallback:
            seen[u] = None
            if len(seen) >= limit:
                break
    result.urls = list(seen.keys())[:limit]
    return result


def crawl_social_flat(
    url: str,
    settings: Settings,
    *,
    mode: CrawlMode,
    limit: int,
    platform: str,
) -> CrawlResult:
    """Instagram / Facebook / TikTok / generic profile expansion via flat extract."""
    result = CrawlResult(
        mode=mode,
        platform=platform,
        auth_required=crawl_requires_auth(mode),
        auth_configured=cookie_auth_configured(settings),
        tabs_tried=["flat"],
    )
    if mode == CrawlMode.SHALLOW:
        result.urls = resolve_url(url, settings, playlist_end=limit)
        return result

    urls, err = _extract_flat_paged(url.strip(), settings, playlist_end=limit)
    if err:
        result.errors.append(err)
        logging.warning("Social crawl failed %s: %s", url, err)
        # Soft fallback to shallow single-pass
        result.urls = resolve_flat(url, settings, playlist_end=limit)
    else:
        result.urls = urls[:limit]
    return result


def crawl_profile(
    url: str,
    settings: Settings,
    *,
    mode: CrawlMode | str = CrawlMode.SHALLOW,
    limit: int = 50,
    pace_seconds: Optional[float] = None,
    sleep_fn: SleepFn = time.sleep,
    require_auth: bool = True,
) -> CrawlResult:
    """
    Expand a profile / channel URL into media item URLs.

    Deep modes (deep / videos / shorts / posts) require cookie auth when
    ``require_auth`` is True (default). Shallow mode always runs.
    """
    crawl_mode = parse_crawl_mode(mode)
    item_limit = clamp_crawl_limit(limit)
    pace = (
        float(settings.pace_seconds)
        if pace_seconds is None
        else max(0.0, float(pace_seconds))
    )
    auth_ok = cookie_auth_configured(settings)
    needs_auth = crawl_requires_auth(crawl_mode)

    if require_auth and needs_auth and not auth_ok:
        raise CrawlAuthError(
            "Deep crawl modes need cookie auth. Set COOKIES_FROM_BROWSER "
            "(e.g. brave:Default) or COOKIES_FILE in Settings, then retry."
        )

    platform = detect_platform(url)
    if platform == "spotify":
        # Metadata bridge owns catalog URLs; do not deep-crawl Spotify streams.
        return CrawlResult(
            urls=[url.strip()],
            mode=crawl_mode,
            platform=platform,
            auth_required=needs_auth,
            auth_configured=auth_ok,
        )

    if platform == "youtube":
        return crawl_youtube(
            url,
            settings,
            mode=crawl_mode,
            limit=item_limit,
            pace_seconds=pace,
            sleep_fn=sleep_fn,
        )

    return crawl_social_flat(
        url,
        settings,
        mode=crawl_mode,
        limit=item_limit,
        platform=platform,
    )


def crawl_many(
    urls: Sequence[str],
    settings: Settings,
    *,
    mode: CrawlMode | str = CrawlMode.SHALLOW,
    limit: int = 50,
    pace_seconds: Optional[float] = None,
    sleep_fn: SleepFn = time.sleep,
    require_auth: bool = True,
) -> CrawlResult:
    """Crawl multiple seed URLs; merge and dedupe up to ``limit`` total items."""
    crawl_mode = parse_crawl_mode(mode)
    item_limit = clamp_crawl_limit(limit)
    pace = (
        float(settings.pace_seconds)
        if pace_seconds is None
        else max(0.0, float(pace_seconds))
    )
    merged: dict[str, None] = {}
    tabs: List[str] = []
    errors: List[str] = []
    platforms: List[str] = []
    for i, raw in enumerate(urls):
        text = (raw or "").strip()
        if not text or text.startswith("#"):
            continue
        if i > 0 and pace > 0:
            sleep_fn(pace)
        remaining = item_limit - len(merged)
        if remaining <= 0:
            break
        one = crawl_profile(
            text,
            settings,
            mode=crawl_mode,
            limit=remaining,
            pace_seconds=pace,
            sleep_fn=sleep_fn,
            require_auth=require_auth,
        )
        platforms.append(one.platform)
        tabs.extend(one.tabs_tried)
        errors.extend(one.errors)
        for u in one.urls:
            if u not in merged:
                merged[u] = None
            if len(merged) >= item_limit:
                break
    return CrawlResult(
        urls=list(merged.keys())[:item_limit],
        mode=crawl_mode,
        platform=platforms[0] if len(set(platforms)) == 1 else "mixed",
        tabs_tried=tabs,
        errors=errors,
        auth_required=crawl_requires_auth(crawl_mode),
        auth_configured=cookie_auth_configured(settings),
    )
