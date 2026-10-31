"""URL / playlist / channel / profile resolvers via yt-dlp."""

from __future__ import annotations

import logging
import re
from typing import List, Sequence
from urllib.parse import urlparse

from ytscore.cache import title_cache
from ytscore.rule34_video import (
    PLATFORM_ID as RULE34_VIDEO_PLATFORM,
    is_rule34_video_host,
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

# Host fragments for adult-tube site class (yt-dlp extractors; cookie auth for
# private / unlisted / age-gated surfaces the signed-in session can already reach).
_ADULT_TUBE_HOST_MARKERS = (
    "pornhub",
    "youporn",
    "redtube",
    "tube8",
    "xtube",
    "spankbang",
    "xvideos",
    "xnxx",
    "xhamster",
)

_PLAYLIST_PATH_RE = re.compile(
    r"/(?:playlist|playlists|album|albums|favourite|favorite|watchlater)(?:/|$|\?)",
    re.IGNORECASE,
)


def _require_yt_dlp():
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed")
    return yt_dlp


def detect_platform(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if "youtube" in host or "youtu.be" in host:
        return "youtube"
    if "instagram" in host:
        return "instagram"
    if "facebook" in host or "fb.watch" in host:
        return "facebook"
    if "tiktok" in host:
        return "tiktok"
    if "spotify" in host:
        return "spotify"
    if is_rule34_video_host(url):
        return RULE34_VIDEO_PLATFORM
    if any(marker in host for marker in _ADULT_TUBE_HOST_MARKERS):
        return "adult_tube"
    return "generic"


def is_playlist_url(url: str) -> bool:
    """True when the path looks like a playlist / album / watch-later collection."""
    parsed = urlparse((url or "").strip())
    path = parsed.path or ""
    if _PLAYLIST_PATH_RE.search(path):
        return True
    # Query-style playlist markers used by some tube hosts.
    query = (parsed.query or "").lower()
    return "playlist" in query or "pkey=" in query


def private_playlist_needs_cookies(url: str) -> bool:
    """
    Adult-tube (and similar) private / unlisted playlists need cookie auth.

    Public playlists may resolve without cookies; private ones only enumerate
    when the configured browser profile or cookie file is signed in. This does
    not bypass DRM, paywalls, or sessions the user cannot already open.
    """
    platform = detect_platform(url)
    return platform == "adult_tube" and is_playlist_url(url)


class PlaylistAuthError(RuntimeError):
    """Raised when a private/unlisted playlist resolve needs cookies that are missing."""


def _entry_to_url(entry: dict, *, base_url: str) -> str:
    if not entry:
        return ""
    entry_url = entry.get("url") or entry.get("webpage_url") or ""
    entry_id = entry.get("id")
    if entry_url:
        return canonicalize_media_url(str(entry_url), base_url=base_url)
    if entry_id and detect_platform(base_url) == "youtube":
        return f"https://www.youtube.com/watch?v={entry_id}"
    if entry_id and detect_platform(base_url) == "adult_tube":
        host = urlparse(base_url).hostname or "www.pornhub.com"
        return canonicalize_media_url(
            f"https://{host}/view_video.php?viewkey={entry_id}"
        )
    if entry_id and detect_platform(base_url) == RULE34_VIDEO_PLATFORM:
        host = urlparse(base_url).hostname or "rule34video.com"
        # Slug-less video URLs 404 on this host; keep id path as a last resort.
        return canonicalize_media_url(f"https://{host}/video/{entry_id}/placeholder/")
    return ""


def resolve_youtube(url: str, settings: Settings, playlist_end: int = 100) -> List[str]:
    yt_dlp = _require_yt_dlp()
    input_url = canonicalize_media_url(url.strip()) or url.strip()
    if "/watch?" in input_url or "/shorts/" in input_url or "youtu.be/" in input_url:
        return [input_url]

    channel_url = input_url
    for part in (
        "/about",
        "/community",
        "/playlist",
        "/playlists",
        "/streams",
        "/featured",
        "/videos",
        "/shorts",
    ):
        channel_url = channel_url.split(part)[0]

    flat_opts: dict = {"quiet": True, "extract_flat": True}
    if playlist_end > 0:
        flat_opts["playlist_end"] = playlist_end
    ydl_opts = apply_auth_opts(flat_opts, settings)
    links: List[str] = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for tab_path in ("/videos", "/shorts"):
            if playlist_end > 0 and len(links) >= playlist_end:
                break
            try:
                result = ydl.extract_info(f"{channel_url}{tab_path}", download=False)
            except Exception as error:
                logging.warning("Could not extract %s%s: %s", channel_url, tab_path, error)
                continue
            if not isinstance(result, dict) or "entries" not in result:
                continue
            for entry in result["entries"] or []:
                if playlist_end > 0 and len(links) >= playlist_end:
                    break
                if not entry:
                    continue
                resolved = _entry_to_url(entry, base_url=input_url)
                if not resolved:
                    continue
                links.append(resolved)
                title_cache.put(resolved, entry.get("title"))

    if not links:
        # Fallback: treat as playlist / single extract
        return resolve_flat(input_url, settings, playlist_end=playlist_end)
    return list(dict.fromkeys(links))


def resolve_flat(url: str, settings: Settings, playlist_end: int = 100) -> List[str]:
    yt_dlp = _require_yt_dlp()
    input_url = canonicalize_media_url(url.strip()) or url.strip()
    flat_opts: dict = {"quiet": True, "extract_flat": True}
    if playlist_end > 0:
        flat_opts["playlist_end"] = playlist_end
    ydl_opts = apply_auth_opts(flat_opts, settings)
    links: List[str] = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(input_url, download=False)
    except Exception as error:
        logging.warning("Could not extract links from %s: %s", input_url, error)
        return []

    entries = result.get("entries") if isinstance(result, dict) else None
    if entries:
        for entry in entries:
            if playlist_end > 0 and len(links) >= playlist_end:
                break
            if not entry:
                continue
            resolved = _entry_to_url(entry, base_url=input_url)
            entry_title = entry.get("title") if isinstance(entry, dict) else None
            if resolved:
                links.append(resolved)
                title_cache.put(resolved, entry_title)
        if links:
            return list(dict.fromkeys(links))
    if isinstance(result, dict):
        page = result.get("webpage_url") or result.get("url") or input_url
        title = result.get("title")
        resolved = canonicalize_media_url(str(page), base_url=input_url) or input_url
        title_cache.put(resolved, title)
        return [resolved]
    return [input_url]


def _cookie_auth_configured(settings: Settings) -> bool:
    if settings.cookies_tuple():
        return True
    return bool((settings.cookies_file or "").strip())


def resolve_adult_tube(
    url: str,
    settings: Settings,
    playlist_end: int = 100,
    *,
    require_playlist_cookies: bool = False,
) -> List[str]:
    """
    Resolve adult-tube video / playlist / model URLs via yt-dlp.

    Private or unlisted playlists only enumerate when cookie auth is configured
    (browser profile or file) for a session that can already open them. Public
    singles / public playlists may work anonymously; TLS impersonation
    (curl_cffi) is recommended. Set ``require_playlist_cookies=True`` to refuse
    playlist resolves without cookies (Suite default for private-path safety).
    """
    input_url = canonicalize_media_url(url.strip()) or url.strip()
    needs_cookies = private_playlist_needs_cookies(input_url)
    if needs_cookies and require_playlist_cookies and not _cookie_auth_configured(settings):
        raise PlaylistAuthError(
            "Private / unlisted playlists need cookie auth. Set "
            "COOKIES_FROM_BROWSER (e.g. brave:Default) or COOKIES_FILE in "
            "Settings, then retry. Only surfaces your signed-in session can open."
        )
    if needs_cookies and not _cookie_auth_configured(settings):
        logging.warning(
            "Adult-tube playlist resolve without cookies; private/unlisted "
            "entries will be missing. Configure COOKIES_FROM_BROWSER or COOKIES_FILE."
        )
    links = resolve_flat(input_url, settings, playlist_end=playlist_end)
    if needs_cookies and not links and not _cookie_auth_configured(settings):
        raise PlaylistAuthError(
            "Playlist resolve returned no items and cookies are not configured. "
            "Private / unlisted playlists need COOKIES_FROM_BROWSER or COOKIES_FILE."
        )
    return links


def resolve_rule34_video(
    url: str,
    settings: Settings,
    playlist_end: int = 100,
) -> List[str]:
    """
    Resolve rule34video.com singles and listing / tag / member / search URLs.

    Singles return the canonical video page URL. Listings use clean-room HTML
    harvest (yt-dlp has no flat playlist extractor for this host). Cookies help
    for age-gated or account-restricted surfaces.
    """
    input_url = canonicalize_media_url(url.strip()) or url.strip()
    if is_rule34_video_single_url(input_url):
        # Host requires the slug segment; /video/<id>/ alone 404s. Only
        # normalize plural /videos/ → /video/ while keeping the rest of the path.
        parsed = urlparse(input_url)
        path = parsed.path or ""
        if path.lower().startswith("/videos/"):
            path = "/video/" + path[len("/videos/") :]
        host = parsed.hostname or "rule34video.com"
        canonical = canonicalize_media_url(
            f"https://{host}{path}"
            + (("?" + parsed.query) if parsed.query else "")
        )
        return [canonical]
    if is_rule34_video_listing_url(input_url):
        # ~20 thumbs per page on this host; playlist_end 0 → paced multi-page.
        if playlist_end <= 0:
            max_pages = 25
        else:
            max_pages = min(50, max(1, 1 + (playlist_end - 1) // 20))
        links = resolve_listing_pages(
            input_url,
            settings,
            limit=playlist_end,
            max_pages=max_pages,
            pace_seconds=float(getattr(settings, "pace_seconds", 0) or 0),
        )
        return links or [input_url]
    return resolve_flat(input_url, settings, playlist_end=playlist_end)


def resolve_url(url: str, settings: Settings, playlist_end: int = 100) -> List[str]:
    platform = detect_platform(url)
    if platform == "youtube":
        return resolve_youtube(url, settings, playlist_end=playlist_end)
    if platform == "spotify":
        return [canonicalize_media_url(url.strip()) or url.strip()]
    if platform == RULE34_VIDEO_PLATFORM:
        return resolve_rule34_video(url, settings, playlist_end=playlist_end)
    if platform == "adult_tube":
        # Playlist seeds require cookies (private/unlisted path); singles do not.
        return resolve_adult_tube(
            url,
            settings,
            playlist_end=playlist_end,
            require_playlist_cookies=True,
        )
    return resolve_flat(url, settings, playlist_end=playlist_end)


def resolve_many(urls: Sequence[str], settings: Settings, playlist_end: int = 100) -> List[str]:
    out: List[str] = []
    for raw in urls:
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        out.extend(resolve_url(text, settings, playlist_end=playlist_end))
    return list(dict.fromkeys(out))


def auth_probe(url: str, settings: Settings) -> None:
    yt_dlp = _require_yt_dlp()
    ydl_opts = apply_auth_opts(
        {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "playlist_end": 1,
        },
        settings,
    )
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(
            canonicalize_media_url(url.strip()) or url.strip(),
            download=False,
        )
