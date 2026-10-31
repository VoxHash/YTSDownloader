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
from urllib.parse import urlparse

from ytscore.adult_tube import (
    TAB_GIFS,
    TAB_PHOTOS,
    adult_tube_profile_root,
    adult_tube_tabs_for_mode,
    expand_album_to_photos,
    fetch_html,
    harvest_profile_listing,
    is_adult_tube_album_url,
    is_adult_tube_profile_url,
    is_adult_tube_single_url,
    tab_uses_html_harvest,
)
from ytscore.backoff import compute_backoff_seconds, is_rate_limited
from ytscore.cache import title_cache
from ytscore.resolvers import detect_platform, resolve_flat, resolve_url
from ytscore.rule34_video import (
    PLATFORM_ID as RULE34_VIDEO_PLATFORM,
    is_rule34_video_listing_url,
    is_rule34_video_single_url,
    resolve_listing_pages,
)
from ytscore.settings import Settings, apply_auth_opts
from ytscore.util import canonicalize_media_url

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
    CrawlMode.SHORTS: "Shorts / clips / GIFs (cookie auth)",
    CrawlMode.POSTS: "Posts / reels / albums (cookie auth)",
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


# Soft UI / clamp ceiling for positive limits. ``0`` means unlimited.
CRAWL_LIMIT_MAX = 10000


def clamp_crawl_limit(
    limit: int, *, default: int = 50, maximum: int = CRAWL_LIMIT_MAX
) -> int:
    """Clamp a crawl item budget.

    ``0`` means unlimited (no item cap). Positive values are clamped to
    ``1..maximum`` (default maximum ``CRAWL_LIMIT_MAX`` = 10000).
    """
    try:
        n = int(limit)
    except (TypeError, ValueError):
        n = default
    if n < 0:
        n = 0
    if n == 0:
        return 0
    if maximum > 0 and n > maximum:
        n = maximum
    return n


def crawl_budget_exhausted(count: int, limit: int) -> bool:
    """True when a positive limit has been reached (``0`` = unlimited)."""
    return limit > 0 and count >= limit


def take_crawl_budget(items: Sequence[str], limit: int) -> List[str]:
    """Return ``items`` truncated to ``limit`` when limit is positive."""
    seq = list(items)
    if limit <= 0:
        return seq
    return seq[:limit]


def remaining_crawl_budget(have: int, limit: int) -> int:
    """Slots left under ``limit``. ``0`` means unlimited (pass through as 0)."""
    if limit <= 0:
        return 0
    return max(0, limit - max(0, int(have)))


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


def _entries_to_urls(
    entries: Sequence[object],
    *,
    limit: int,
    base_url: str = "",
    platform: str = "generic",
) -> List[str]:
    links: List[str] = []
    for entry in entries or []:
        if crawl_budget_exhausted(len(links), limit):
            break
        if not entry or not isinstance(entry, dict):
            continue
        entry_url = entry.get("url") or entry.get("webpage_url")
        entry_id = entry.get("id")
        entry_title = entry.get("title")
        if entry_url:
            resolved = canonicalize_media_url(str(entry_url), base_url=base_url or None)
            if resolved.startswith("http"):
                links.append(resolved)
                title_cache.put(resolved, entry_title)
                continue
        if entry_id:
            if platform == "adult_tube" and base_url:
                host = urlparse(base_url).hostname or "www.pornhub.com"
                resolved = canonicalize_media_url(
                    f"https://{host}/view_video.php?viewkey={entry_id}"
                )
            else:
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
    """Return (urls, error_message). ``playlist_end`` 0 = unlimited."""
    ydl = _require_yt_dlp()
    flat_opts: dict = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
    }
    if playlist_end > 0:
        flat_opts["playlist_end"] = playlist_end
    ydl_opts = apply_auth_opts(flat_opts, settings)
    try:
        with ydl.YoutubeDL(ydl_opts) as client:
            result = client.extract_info(url, download=False)
    except Exception as error:
        return [], str(error)

    if not isinstance(result, dict):
        return [], "unexpected extractor payload"
    platform = detect_platform(url)
    entries = result.get("entries")
    if entries:
        return (
            _entries_to_urls(
                list(entries),
                limit=playlist_end,
                base_url=url,
                platform=platform,
            ),
            None,
        )
    # Single item
    page = result.get("webpage_url") or result.get("url") or url
    title = result.get("title")
    resolved = canonicalize_media_url(str(page), base_url=url) if page else url
    if resolved.startswith("http"):
        title_cache.put(resolved, title)
        return [resolved], None
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
        if crawl_budget_exhausted(len(seen), limit):
            break
        tab_url = f"{root}{tab}"
        result.tabs_tried.append(tab)
        if i > 0:
            _paced_sleep(pace_seconds, sleep_fn=sleep_fn, settings=settings)
        remaining = remaining_crawl_budget(len(seen), limit)
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
            if crawl_budget_exhausted(len(seen), limit):
                break

    if not seen:
        # Fallback: treat as playlist / channel flat extract
        fallback = resolve_flat(input_url, settings, playlist_end=limit)
        for u in fallback:
            seen[u] = None
            if crawl_budget_exhausted(len(seen), limit):
                break
    result.urls = take_crawl_budget(list(seen.keys()), limit)
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
        result.urls = take_crawl_budget(urls, limit)
    return result


def _extract_adult_tube_html_tab(
    tab_url: str,
    settings: Settings,
    *,
    tab: str,
    limit: int,
) -> tuple[List[str], Optional[str]]:
    """Harvest GIF / album page URLs from profile listing HTML."""
    html, err = fetch_html(tab_url, settings)
    if err:
        return [], err
    kinds: List[str] = []
    if tab.rstrip("/") == TAB_GIFS.rstrip("/") or tab == TAB_GIFS:
        kinds.append("gif")
    if tab.rstrip("/") == TAB_PHOTOS.rstrip("/") or tab == TAB_PHOTOS:
        kinds.append("album")
    if not kinds:
        kinds = ["gif", "album"]
    return (
        harvest_profile_listing(html, base_url=tab_url, kinds=kinds, limit=limit),
        None,
    )


def crawl_adult_tube(
    url: str,
    settings: Settings,
    *,
    mode: CrawlMode,
    limit: int,
    pace_seconds: float,
    sleep_fn: SleepFn = time.sleep,
) -> CrawlResult:
    """
    Paced model/user tab crawl for adult-tube hosts.

    Video tabs use yt-dlp flat extract. GIF and photos tabs use clean-room HTML
    link harvest (yt-dlp wrongly collapses those paths onto /videos). Album seeds
    expand to photo pages under deep/posts modes. Cookie auth required for deep
    modes (caller enforces).
    """
    platform = "adult_tube"
    result = CrawlResult(
        mode=mode,
        platform=platform,
        auth_required=crawl_requires_auth(mode),
        auth_configured=cookie_auth_configured(settings),
    )
    input_url = canonicalize_media_url(url.strip()) or url.strip()

    if is_adult_tube_album_url(input_url) and mode in (
        CrawlMode.DEEP,
        CrawlMode.POSTS,
    ):
        photos, err = expand_album_to_photos(input_url, settings, limit=limit)
        if err:
            result.errors.append(err)
            result.urls = [input_url]
        else:
            result.tabs_tried.append("album→photos")
            result.urls = take_crawl_budget(photos, limit) or [input_url]
        return result

    if is_adult_tube_single_url(input_url):
        result.urls = [input_url]
        return result

    if mode == CrawlMode.SHALLOW:
        result.urls = resolve_url(input_url, settings, playlist_end=limit)
        return result

    root = adult_tube_profile_root(input_url)
    if not root or not is_adult_tube_profile_url(input_url):
        # Playlist / generic adult-tube URL: flat extract only.
        return crawl_social_flat(
            input_url,
            settings,
            mode=mode,
            limit=limit,
            platform=platform,
        )

    tabs = adult_tube_tabs_for_mode(mode.value)
    seen: dict[str, None] = {}
    attempt = 0
    for i, tab in enumerate(tabs):
        if crawl_budget_exhausted(len(seen), limit):
            break
        tab_url = f"{root}{tab}"
        result.tabs_tried.append(tab)
        if i > 0:
            _paced_sleep(pace_seconds, sleep_fn=sleep_fn, settings=settings)
        remaining = remaining_crawl_budget(len(seen), limit)
        if tab_uses_html_harvest(tab):
            urls, err = _extract_adult_tube_html_tab(
                tab_url, settings, tab=tab, limit=remaining
            )
        else:
            urls, err = _extract_flat_paged(
                tab_url, settings, playlist_end=remaining
            )
        if err:
            result.errors.append(f"{tab}: {err}")
            logging.warning("Adult-tube crawl tab failed %s: %s", tab_url, err)
            attempt += 1
            _paced_sleep(
                pace_seconds,
                sleep_fn=sleep_fn,
                attempt=attempt,
                rate_limited=is_rate_limited(err),
                settings=settings,
            )
            continue
        # Deep/posts: expand harvested albums into photo pages (budget-limited).
        expand_albums = mode in (CrawlMode.DEEP, CrawlMode.POSTS) and tab_uses_html_harvest(
            tab
        )
        for item in urls:
            if crawl_budget_exhausted(len(seen), limit):
                break
            if expand_albums and is_adult_tube_album_url(item):
                _paced_sleep(pace_seconds, sleep_fn=sleep_fn, settings=settings)
                photos, album_err = expand_album_to_photos(
                    item,
                    settings,
                    limit=remaining_crawl_budget(len(seen), limit),
                )
                if album_err:
                    result.errors.append(f"album {item}: {album_err}")
                    if item not in seen:
                        seen[item] = None
                    continue
                for photo in photos:
                    if photo not in seen:
                        seen[photo] = None
                    if crawl_budget_exhausted(len(seen), limit):
                        break
                continue
            if item not in seen:
                seen[item] = None

    if not seen:
        fallback = resolve_flat(input_url, settings, playlist_end=limit)
        for u in fallback:
            seen[u] = None
            if crawl_budget_exhausted(len(seen), limit):
                break
    result.urls = take_crawl_budget(list(seen.keys()), limit)
    return result


def crawl_rule34_video(
    url: str,
    settings: Settings,
    *,
    mode: CrawlMode,
    limit: int,
    pace_seconds: float,
    sleep_fn: SleepFn = time.sleep,
) -> CrawlResult:
    """
    Paced listing crawl for the rule34video.com host class.

    Singles pass through. Shallow harvests the first listing page (or resolves
    via ``resolve_url``). Deep / Videos paginate listing / tag / member / search
    feeds. Shorts / Posts fall back to the same video listing (no GIF/album
    tabs on this host).
    """
    platform = RULE34_VIDEO_PLATFORM
    result = CrawlResult(
        mode=mode,
        platform=platform,
        auth_required=crawl_requires_auth(mode),
        auth_configured=cookie_auth_configured(settings),
    )
    input_url = canonicalize_media_url(url.strip()) or url.strip()

    if is_rule34_video_single_url(input_url):
        result.urls = resolve_url(input_url, settings, playlist_end=1)
        return result

    if mode == CrawlMode.SHALLOW or not is_rule34_video_listing_url(input_url):
        result.urls = resolve_url(input_url, settings, playlist_end=limit)
        result.tabs_tried.append("shallow")
        return result

    if limit <= 0:
        max_pages = 25
    else:
        max_pages = min(50, max(1, 1 + (limit - 1) // 20))
    result.tabs_tried.append("listing")
    links = resolve_listing_pages(
        input_url,
        settings,
        limit=limit,
        max_pages=max_pages,
        pace_seconds=pace_seconds,
        sleep_fn=sleep_fn,
    )
    result.urls = take_crawl_budget(links, limit) or resolve_url(
        input_url, settings, playlist_end=limit
    )
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

    if platform == "adult_tube":
        return crawl_adult_tube(
            url,
            settings,
            mode=crawl_mode,
            limit=item_limit,
            pace_seconds=pace,
            sleep_fn=sleep_fn,
        )

    if platform == RULE34_VIDEO_PLATFORM:
        return crawl_rule34_video(
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
        if crawl_budget_exhausted(len(merged), item_limit):
            break
        remaining = remaining_crawl_budget(len(merged), item_limit)
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
            if crawl_budget_exhausted(len(merged), item_limit):
                break
    return CrawlResult(
        urls=take_crawl_budget(list(merged.keys()), item_limit),
        mode=crawl_mode,
        platform=platforms[0] if len(set(platforms)) == 1 else "mixed",
        tabs_tried=tabs,
        errors=errors,
        auth_required=crawl_requires_auth(crawl_mode),
        auth_configured=cookie_auth_configured(settings),
    )
