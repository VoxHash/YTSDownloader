"""Clean-room adult-tube profile tab helpers (beyond yt-dlp flat extract).

Enumerates model/user videos, GIF/clip listings, and album/photo pages using
the Suite auth stack (yt-dlp networking + cookies + TLS impersonation). Does
not vendor AGPL scrapers; only surfaces the signed-in session can already open.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Sequence
from urllib.parse import urljoin, urlparse

from ytscore.settings import Settings, apply_auth_opts
from ytscore.util import canonicalize_media_url

try:
    import yt_dlp
except ImportError:  # pragma: no cover
    yt_dlp = None

# Profile roots that expose video / gif / photos tabs on MindGeek-family hosts.
_PROFILE_ROOT_RE = re.compile(
    r"^(https?://[^/?#]+)/(?:model|pornstar|users|user|channels|channel)/"
    r"(?P<id>[^/?#]+)",
    re.IGNORECASE,
)

_SINGLE_VIDEO_RE = re.compile(
    r"(?:view_video\.php|/watch/|/embed/|/video[./]|/videos/\d)",
    re.IGNORECASE,
)
_GIF_PATH_RE = re.compile(r"/gif/(\d+)", re.IGNORECASE)
_ALBUM_PATH_RE = re.compile(r"/album/(\d+)", re.IGNORECASE)
_PHOTO_PATH_RE = re.compile(r"/photo/(\d+)", re.IGNORECASE)

_GIF_ID_ATTR_RE = re.compile(r"""id=["']gif(\d+)["']""", re.IGNORECASE)
_ALBUM_PHOTO_ATTR_RE = re.compile(r"""id=["']albumphoto(\d+)["']""", re.IGNORECASE)
_HREF_ALBUM_RE = re.compile(r"""href=["']([^"']*/album/\d+[^"']*)["']""", re.IGNORECASE)
_HREF_PHOTO_RE = re.compile(r"""href=["']([^"']*/photo/\d+[^"']*)["']""", re.IGNORECASE)
_HREF_GIF_RE = re.compile(r"""href=["']([^"']*/gif/\d+[^"']*)["']""", re.IGNORECASE)

# Tab suffixes for paced deep crawl (relative to profile root).
TAB_VIDEOS = "/videos"
TAB_UPLOADS = "/videos/upload"
TAB_GIFS = "/gifs"
TAB_PHOTOS = "/photos"

_HTML_TAB_SUFFIXES = frozenset({TAB_GIFS, TAB_PHOTOS})


def is_adult_tube_profile_url(url: str) -> bool:
    """True when the URL is a model / user / channel profile (any tab)."""
    return bool(_PROFILE_ROOT_RE.match((url or "").strip()))


def adult_tube_profile_root(url: str) -> Optional[str]:
    """Return ``https://host/kind/id`` without tab suffixes, or None."""
    text = (url or "").strip()
    if not _PROFILE_ROOT_RE.match(text):
        return None
    path = urlparse(text).path or ""
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        return None
    host = (urlparse(text).hostname or "").lower()
    return f"https://{host}/{parts[0]}/{parts[1]}"


def is_adult_tube_single_url(url: str) -> bool:
    """True for a single video / gif / album / photo page (not a profile list)."""
    text = (url or "").strip()
    if not text:
        return False
    path = urlparse(text).path or ""
    query = urlparse(text).query or ""
    if _GIF_PATH_RE.search(path) or _ALBUM_PATH_RE.search(path) or _PHOTO_PATH_RE.search(
        path
    ):
        return True
    if is_adult_tube_profile_url(text):
        return False
    if _SINGLE_VIDEO_RE.search(path) or "viewkey=" in query.lower():
        return True
    return False


def is_adult_tube_gif_url(url: str) -> bool:
    return bool(_GIF_PATH_RE.search(urlparse((url or "").strip()).path or ""))


def is_adult_tube_album_url(url: str) -> bool:
    return bool(_ALBUM_PATH_RE.search(urlparse((url or "").strip()).path or ""))


def is_adult_tube_photo_url(url: str) -> bool:
    return bool(_PHOTO_PATH_RE.search(urlparse((url or "").strip()).path or ""))


def adult_tube_tabs_for_mode(mode: str) -> List[str]:
    """Map crawl mode value → profile tab path suffixes."""
    key = (mode or "").strip().lower()
    if key == "videos":
        return [TAB_VIDEOS, TAB_UPLOADS]
    if key == "shorts":
        return [TAB_GIFS]
    if key == "posts":
        return [TAB_PHOTOS]
    if key == "deep":
        return [TAB_VIDEOS, TAB_UPLOADS, TAB_GIFS, TAB_PHOTOS]
    return [TAB_VIDEOS]


def tab_uses_html_harvest(tab: str) -> bool:
    """GIF / photos tabs are not correctly enumerated by yt-dlp flat extract."""
    return tab.rstrip("/") in _HTML_TAB_SUFFIXES or tab in _HTML_TAB_SUFFIXES


def fetch_html(url: str, settings: Settings) -> tuple[str, Optional[str]]:
    """Fetch page HTML via yt-dlp networking (cookies + impersonate)."""
    if yt_dlp is None:
        return "", "yt-dlp is not installed"
    input_url = canonicalize_media_url(url.strip()) or url.strip()
    ydl_opts = apply_auth_opts({"quiet": True, "skip_download": True}, settings)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            resp = ydl.urlopen(input_url)
            data = resp.read()
    except Exception as error:
        return "", str(error)
    if isinstance(data, bytes):
        return data.decode("utf-8", "replace"), None
    return str(data), None


def _abs(base_url: str, href: str) -> str:
    return canonicalize_media_url(urljoin(base_url, href), base_url=base_url)


def harvest_profile_listing(
    html: str,
    *,
    base_url: str,
    kinds: Sequence[str],
    limit: int,
) -> List[str]:
    """
    Extract item page URLs from a profile GIF or photos listing.

    ``kinds`` may include ``gif`` and/or ``album``.
    """
    # limit <= 0 means unlimited (Suite crawl budget 0).
    if not html or limit < 0:
        return []
    want_gif = "gif" in kinds
    want_album = "album" in kinds
    seen: dict[str, None] = {}
    host_base = canonicalize_media_url(base_url) or base_url

    def _budget_full() -> bool:
        return limit > 0 and len(seen) >= limit

    def _add(url: str) -> None:
        if not url or _budget_full():
            return
        cleaned = canonicalize_media_url(url, base_url=host_base)
        if cleaned.startswith("http") and cleaned not in seen:
            seen[cleaned] = None

    if want_gif:
        for gif_id in _GIF_ID_ATTR_RE.findall(html):
            _add(_abs(host_base, f"/gif/{gif_id}"))
            if _budget_full():
                return list(seen.keys())
        for href in _HREF_GIF_RE.findall(html):
            _add(_abs(host_base, href))
            if _budget_full():
                return list(seen.keys())

    if want_album:
        for href in _HREF_ALBUM_RE.findall(html):
            # Skip /albums index / search noise.
            if re.search(r"/album/\d+", href, re.IGNORECASE):
                _add(_abs(host_base, href))
            if _budget_full():
                return list(seen.keys())
        for album_id in _ALBUM_PHOTO_ATTR_RE.findall(html):
            _add(_abs(host_base, f"/album/{album_id}"))
            if _budget_full():
                return list(seen.keys())

    return list(seen.keys())


def harvest_album_photos(
    html: str,
    *,
    base_url: str,
    limit: int,
) -> List[str]:
    """Extract ``/photo/<id>`` page URLs from an album HTML page."""
    # limit <= 0 means unlimited.
    if not html or limit < 0:
        return []
    seen: dict[str, None] = {}
    host_base = canonicalize_media_url(base_url) or base_url
    for href in _HREF_PHOTO_RE.findall(html):
        cleaned = canonicalize_media_url(urljoin(host_base, href), base_url=host_base)
        if cleaned.startswith("http") and cleaned not in seen:
            seen[cleaned] = None
        if limit > 0 and len(seen) >= limit:
            break
    return list(seen.keys())


def expand_album_to_photos(
    album_url: str,
    settings: Settings,
    *,
    limit: int,
) -> tuple[List[str], Optional[str]]:
    """Fetch an album page and return photo page URLs (up to ``limit``)."""
    html, err = fetch_html(album_url, settings)
    if err:
        return [], err
    return harvest_album_photos(html, base_url=album_url, limit=limit), None


def resolve_gif_media_url(page_url: str, settings: Settings) -> Optional[str]:
    """Resolve a ``/gif/<id>`` page to a direct .gif / .mp4 / .webm CDN URL."""
    match = _GIF_PATH_RE.search(urlparse(page_url).path or "")
    if not match:
        return None
    gif_id = match.group(1)
    html, err = fetch_html(page_url, settings)
    if err or not html:
        logging.warning("GIF page fetch failed %s: %s", page_url, err)
        return None
    # Prefer media whose path/filename contains this gif id.
    candidates: List[str] = []
    for attr in ("data-gif-url", "data-mp4", "data-webm", "src"):
        for found in re.findall(
            rf"""{attr}=["']([^"']*{re.escape(gif_id)}[^"']*)["']""",
            html,
            re.IGNORECASE,
        ):
            candidates.append(found)
    for found in re.findall(
        rf"""https?://[^"'\s<>]*/pics/gifs/[^"'\s<>]*{re.escape(gif_id)}[^"'\s<>]*""",
        html,
        re.IGNORECASE,
    ):
        candidates.append(found)

    def _rank(url: str) -> tuple[int, int]:
        lower = url.lower()
        # Prefer mp4/webm over animated gif; prefer non-jpg.
        ext_score = 0
        if ".mp4" in lower:
            ext_score = 0
        elif ".webm" in lower:
            ext_score = 1
        elif ".gif" in lower and ".jpg" not in lower:
            ext_score = 2
        else:
            ext_score = 9
        return (ext_score, len(url))

    media = [u for u in candidates if re.search(r"\.(?:mp4|webm|gif)(?:\?|$)", u, re.I)]
    if not media:
        return None
    media.sort(key=_rank)
    return canonicalize_media_url(media[0]) or media[0]


def resolve_photo_media_url(page_url: str, settings: Settings) -> Optional[str]:
    """Resolve a ``/photo/<id>`` page to a direct image CDN URL."""
    match = _PHOTO_PATH_RE.search(urlparse(page_url).path or "")
    if not match:
        return None
    photo_id = match.group(1)
    html, err = fetch_html(page_url, settings)
    if err or not html:
        logging.warning("Photo page fetch failed %s: %s", page_url, err)
        return None
    candidates: List[str] = []
    og = re.findall(
        r"""property=["']og:image["'][^>]*content=["']([^"']+)["']""",
        html,
        re.IGNORECASE,
    )
    candidates.extend(og)
    og2 = re.findall(
        r"""content=["']([^"']+)["'][^>]*property=["']og:image["']""",
        html,
        re.IGNORECASE,
    )
    candidates.extend(og2)
    for found in re.findall(
        rf"""https?://[^"'\s<>]*/pics/albums/[^"'\s<>]*{re.escape(photo_id)}[^"'\s<>]*""",
        html,
        re.IGNORECASE,
    ):
        candidates.append(found)
    images = [
        u
        for u in candidates
        if re.search(r"\.(?:jpg|jpeg|png|webp)(?:\?|$)", u, re.I)
    ]
    if not images:
        return None
    # Prefer "original_" filenames when present.
    images.sort(key=lambda u: (0 if "original_" in u else 1, len(u)))
    return canonicalize_media_url(images[0]) or images[0]


def rewrite_adult_tube_media_url(url: str, settings: Settings) -> str:
    """
    Map gif/photo page URLs to direct CDN media for yt-dlp download.

    Video / playlist / album listing URLs are returned unchanged (albums should
    be expanded to photo pages at crawl time).
    """
    text = (url or "").strip()
    if not text:
        return text
    if is_adult_tube_gif_url(text):
        media = resolve_gif_media_url(text, settings)
        if media:
            return media
    if is_adult_tube_photo_url(text):
        media = resolve_photo_media_url(text, settings)
        if media:
            return media
    return text
