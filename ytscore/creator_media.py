"""Clean-room helpers for creator / gallery / clip hosts beyond stock extractors.

Covers browser-companion-class surfaces and related clip / gallery / social hosts:
yt-dlp where an extractor exists; HTML harvest + CDN rewrite when it does not.
Uses Suite auth (cookies + TLS impersonation). Does not vendor third-party
extension source; only surfaces the signed-in session can already open.
"""

from __future__ import annotations

import logging
import os
import re
from typing import List, Optional, Sequence, Tuple
from urllib.parse import unquote, urljoin, urlparse

from ytscore.settings import Settings, apply_auth_opts
from ytscore.util import canonicalize_media_url, clean_filename

try:
    import yt_dlp
except ImportError:  # pragma: no cover
    yt_dlp = None

# Platform ids returned by detect_platform / detect_creator_platform.
PLATFORM_MANYVIDS = "manyvids"
PLATFORM_REDGIFS = "redgifs"
PLATFORM_VIMEO = "vimeo"
PLATFORM_VK = "vk"
PLATFORM_REDDIT = "reddit"
PLATFORM_TWITTER = "twitter"
PLATFORM_CLIPS4SALE = "clips4sale"
PLATFORM_ARYION = "aryion"
PLATFORM_FAPELLO = "fapello"
PLATFORM_PORNPICS = "pornpics"
PLATFORM_TWPORNSTARS = "twpornstars"

# Hosts with working (or partial) yt-dlp extractors — resolve via flat extract.
YTDLP_CREATOR_PLATFORMS = frozenset(
    {
        PLATFORM_MANYVIDS,
        PLATFORM_REDGIFS,
        PLATFORM_VIMEO,
        PLATFORM_VK,
        PLATFORM_REDDIT,
        PLATFORM_TWITTER,
    }
)

# Hosts that need clean-room HTML listing / CDN rewrite.
HTML_CREATOR_PLATFORMS = frozenset(
    {
        PLATFORM_CLIPS4SALE,
        PLATFORM_ARYION,
        PLATFORM_FAPELLO,
        PLATFORM_PORNPICS,
        PLATFORM_TWPORNSTARS,
    }
)

CREATOR_PLATFORMS = YTDLP_CREATOR_PLATFORMS | HTML_CREATOR_PLATFORMS

_HOST_PLATFORM: Tuple[Tuple[Tuple[str, ...], str], ...] = (
    (("manyvids.com",), PLATFORM_MANYVIDS),
    (("redgifs.com",), PLATFORM_REDGIFS),
    (("vimeo.com", "vimeopro.com"), PLATFORM_VIMEO),
    (("vk.com", "vk.ru", "vkvideo.ru"), PLATFORM_VK),
    (("reddit.com", "redd.it", "redditmedia.com"), PLATFORM_REDDIT),
    (("twitter.com", "x.com", "t.co"), PLATFORM_TWITTER),
    (("clips4sale.com",), PLATFORM_CLIPS4SALE),
    (("aryion.com",), PLATFORM_ARYION),
    (("fapello.com",), PLATFORM_FAPELLO),
    (("pornpics.com",), PLATFORM_PORNPICS),
    (("twpornstars.com",), PLATFORM_TWPORNSTARS),
)

_ARYION_VIEW_RE = re.compile(r"^/g4/view/(?P<id>\d+)(?:/|$)", re.IGNORECASE)
_ARYION_VIEW_HREF_RE = re.compile(
    r"""href=["']([^"']*/g4/view/\d+[^"']*)["']""",
    re.IGNORECASE,
)
_ARYION_DATA_RE = re.compile(
    r"""(?:src|href)=["']([^"']*/g4/data/\d+-[^"']+)["']""",
    re.IGNORECASE,
)
_ARYION_DATA_PHP_RE = re.compile(
    r"""(?:src|href)=["']([^"']*data\.php\?id=\d+[^"']*)["']""",
    re.IGNORECASE,
)
_ARYION_FAV_RE = re.compile(
    r"^/g4/(?:favorites|user|gallery|latest\.php|browse\.php|tags\.php)",
    re.IGNORECASE,
)

# Extensions Aryion (and sibling gallery hosts) commonly expose via CDN / data.php.
_DIRECT_EXTENSIONS = (
    ".mp4",
    ".webm",
    ".m4v",
    ".mov",
    ".mkv",
    ".avi",
    ".mpg",
    ".mpeg",
    ".flv",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".avif",
    ".bmp",
    ".pdf",
    ".txt",
    ".rtf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".swf",
    ".zip",
    ".rar",
    ".7z",
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".m4a",
    ".html",
    ".htm",
)
_CONTENT_TYPE_EXTENSION = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/avif": ".avif",
    "image/bmp": ".bmp",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-msvideo": ".avi",
    "video/mpeg": ".mpg",
    "video/x-flv": ".flv",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/rtf": ".rtf",
    "text/rtf": ".rtf",
    "text/plain": ".txt",
    "text/html": ".html",
    "application/x-shockwave-flash": ".swf",
    "application/vnd.adobe.flash.movie": ".swf",
    "application/zip": ".zip",
    "application/x-zip-compressed": ".zip",
    "application/x-rar-compressed": ".rar",
    "application/vnd.rar": ".rar",
    "application/x-7z-compressed": ".7z",
}
_DISPOSITION_FILENAME_RE = re.compile(
    r"""filename\*\s*=\s*(?:UTF-8''|utf-8'')([^;]+)|filename\s*=\s*"([^"]+)"|filename\s*=\s*([^;]+)""",
    re.IGNORECASE,
)

_C4S_CLIP_PATH_RE = re.compile(
    r"^/studio/(?P<studio>\d+)/(?P<clip>\d+)(?:/|$)",
    re.IGNORECASE,
)
_C4S_CLIP_HREF_RE = re.compile(
    r"""href=["']([^"']*/studio/\d+/\d+/[^"']*)["']""",
    re.IGNORECASE,
)
_C4S_CLIPID_HREF_RE = re.compile(
    r"""data-clipid=["'](?P<clip>\d+)["'][^>]*href=["'](?P<href>[^"']+)["']"""
    r"""|href=["'](?P<href2>[^"']+)["'][^>]*data-clipid=["'](?P<clip2>\d+)["']""",
    re.IGNORECASE,
)
_C4S_PREVIEW_RE = re.compile(
    r"""https?://[^"'\\\s]+clips_previews/prev_\d+\.mp4""",
    re.IGNORECASE,
)
_C4S_PREVIEW_KEY_RE = re.compile(
    r"""previewUrl["']?\s*[:=]\s*["'](https?://[^"']+prev_\d+\.mp4[^"']*)["']""",
    re.IGNORECASE,
)

_FAPELLO_MODEL_RE = re.compile(
    r"^/(?P<slug>[a-z0-9][a-z0-9\-]+)/(?:$|(?P<sub>.+))",
    re.IGNORECASE,
)
_FAPELLO_SKIP = frozenset(
    {
        "assets",
        "hot",
        "new",
        "forum",
        "welcome",
        "upload",
        "login",
        "signup",
        "tags",
        "search_v2",
        "search",
        "trending",
        "videos",
        "random",
        "top-uploaders",
        "top-likes",
        "top-followers",
        "content",
        "api",
        "cdn",
    }
)
_FAPELLO_MEDIA_RE = re.compile(
    r"""(?:src|href|data-src)=["'](https?://[^"']+\.(?:jpg|jpeg|png|webp|mp4|gif)[^"']*)["']""",
    re.IGNORECASE,
)
_FAPELLO_CONTENT_HREF_RE = re.compile(
    r"""href=["'](https?://[^"']*fapello\.com/[^"']+/content/[^"']+)["']""",
    re.IGNORECASE,
)

_PORNPICS_GALLERY_RE = re.compile(
    r"^/(?:galleries/)?(?P<a>\d+)(?:/(?P<b>\d+))?/?$",
    re.IGNORECASE,
)
_PORNPICS_HREF_RE = re.compile(
    r"""href=["']((?:https?://(?:www\.)?pornpics\.com)?/(?:galleries/)?\d+/[^"']*)["']""",
    re.IGNORECASE,
)
_PORNPICS_CDN_RE = re.compile(
    r"""(https?://cdni\.pornpics\.com/[^"'\\\s]+\.(?:jpg|jpeg|png|webp))""",
    re.IGNORECASE,
)

_TWPORN_VIDEO_RE = re.compile(r"^/videos?/(?P<id>\d+)", re.IGNORECASE)
_TWPORN_HREF_RE = re.compile(
    r"""href=["']([^"']*/videos?/\d+[^"']*)["']""",
    re.IGNORECASE,
)
_TWPORN_MEDIA_RE = re.compile(
    r"""(?:src|href)=["'](https?://[^"']+\.(?:mp4|webm|jpg|jpeg|png|gif)[^"']*)["']""",
    re.IGNORECASE,
)


def detect_creator_platform(url: str) -> Optional[str]:
    """Return a creator-media platform id, or None when the host is unrelated."""
    host = (urlparse((url or "").strip()).hostname or "").lower()
    if not host:
        return None
    if host.startswith("www."):
        host = host[4:]
    for markers, platform in _HOST_PLATFORM:
        if any(host == m or host.endswith("." + m) for m in markers):
            return platform
    return None


def is_creator_media_host(url: str) -> bool:
    return detect_creator_platform(url) is not None


def fetch_html(url: str, settings: Settings) -> Tuple[str, Optional[str]]:
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


def extract_page_title(html: str) -> str:
    if not html:
        return ""
    for pattern in (
        r"""property=["']og:title["'][^>]*content=["']([^"']+)["']""",
        r"""content=["']([^"']+)["'][^>]*property=["']og:title["']""",
        r"<title[^>]*>([^<]+)</title>",
    ):
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            title = re.sub(r"\s+", " ", match.group(1)).strip()
            title = re.sub(r"\s*[\|\-].*$", "", title).strip() or title
            if title:
                return title
    return ""


# --- Aryion (e621-adjacent gallery / favorites) ---------------------------------


def aryion_view_id(url: str) -> Optional[str]:
    path = urlparse((url or "").strip()).path or ""
    match = _ARYION_VIEW_RE.match(path)
    return match.group("id") if match else None


def is_aryion_single_url(url: str) -> bool:
    return aryion_view_id(url) is not None


def is_aryion_listing_url(url: str) -> bool:
    text = (url or "").strip()
    if not text or detect_creator_platform(text) != PLATFORM_ARYION:
        return False
    if is_aryion_single_url(text):
        return False
    path = urlparse(text).path or "/"
    return bool(_ARYION_FAV_RE.match(path) or path.startswith("/g4/"))


def harvest_aryion_views(html: str, *, base_url: str, limit: int) -> List[str]:
    if not html or limit < 0:
        return []
    seen: dict[str, None] = {}
    for href in _ARYION_VIEW_HREF_RE.findall(html):
        resolved = _abs(base_url, href.split("#", 1)[0])
        if not resolved or aryion_view_id(resolved) is None:
            continue
        if resolved not in seen:
            seen[resolved] = None
        if limit > 0 and len(seen) >= limit:
            break
    return list(seen.keys())


def aryion_data_php_url(view_url_or_id: str) -> str:
    """Canonical original-file endpoint for every Aryion item type."""
    text = (view_url_or_id or "").strip()
    vid = aryion_view_id(text)
    if not vid and text.isdigit():
        vid = text
    if not vid:
        return ""
    return f"https://aryion.com/g4/data.php?id={vid}"


def extract_aryion_media_url(html: str, *, base_url: str) -> str:
    """Prefer data.php (original file) over /g4/data/ HTML/PDF previews."""
    # View pages often embed an HTML conversion of .doc/.docx; data.php returns
    # the uploaded original (pdf/doc/docx/swf/zip/video/audio/image).
    data_php = aryion_data_php_url(base_url)
    if data_php:
        return data_php
    if not html:
        return ""
    for href in _ARYION_DATA_PHP_RE.findall(html):
        resolved = _abs(base_url, href)
        if resolved:
            return resolved
    for href in _ARYION_DATA_RE.findall(html):
        resolved = _abs(base_url, href)
        if resolved:
            return resolved
    match = re.search(
        r"""property=["']og:image["'][^>]*content=["']([^"']+)["']""",
        html,
        re.IGNORECASE,
    )
    if match:
        return canonicalize_media_url(match.group(1), base_url=base_url)
    return ""


# --- Clips4Sale -----------------------------------------------------------------


def clips4sale_ids(url: str) -> Tuple[Optional[str], Optional[str]]:
    path = urlparse((url or "").strip()).path or ""
    match = _C4S_CLIP_PATH_RE.match(path)
    if not match:
        return None, None
    return match.group("studio"), match.group("clip")


def is_clips4sale_single_url(url: str) -> bool:
    studio, clip = clips4sale_ids(url)
    return bool(studio and clip)


def is_clips4sale_listing_url(url: str) -> bool:
    text = (url or "").strip()
    if not text or detect_creator_platform(text) != PLATFORM_CLIPS4SALE:
        return False
    if is_clips4sale_single_url(text):
        return False
    path = (urlparse(text).path or "").lower()
    return any(
        marker in path
        for marker in (
            "/clips/category/",
            "/studio/",
            "/clips/search",
            "/search",
            "/store/",
        )
    )


def harvest_clips4sale_clips(html: str, *, base_url: str, limit: int) -> List[str]:
    if not html or limit < 0:
        return []
    seen: dict[str, None] = {}

    def _add(href: str) -> None:
        if not href:
            return
        resolved = _abs(base_url, href.split("#", 1)[0])
        if not resolved or not is_clips4sale_single_url(resolved):
            return
        if resolved not in seen:
            seen[resolved] = None

    for match in _C4S_CLIPID_HREF_RE.finditer(html):
        href = match.group("href") or match.group("href2") or ""
        _add(href)
        if limit > 0 and len(seen) >= limit:
            return list(seen.keys())
    for href in _C4S_CLIP_HREF_RE.findall(html):
        _add(href)
        if limit > 0 and len(seen) >= limit:
            break
    return list(seen.keys())


def extract_clips4sale_preview_url(html: str) -> str:
    if not html:
        return ""
    keyed = _C4S_PREVIEW_KEY_RE.findall(html)
    if keyed:
        return canonicalize_media_url(keyed[0])
    found = _C4S_PREVIEW_RE.findall(html)
    return canonicalize_media_url(found[0]) if found else ""


# --- Fapello / PornPics / TWPornstars (gallery class) ---------------------------


def is_fapello_model_url(url: str) -> bool:
    if detect_creator_platform(url) != PLATFORM_FAPELLO:
        return False
    path = urlparse((url or "").strip()).path or "/"
    match = _FAPELLO_MODEL_RE.match(path)
    if not match:
        return False
    slug = (match.group("slug") or "").lower()
    return slug not in _FAPELLO_SKIP


def is_fapello_content_url(url: str) -> bool:
    path = (urlparse((url or "").strip()).path or "").lower()
    return detect_creator_platform(url) == PLATFORM_FAPELLO and "/content/" in path


def harvest_fapello_media(html: str, *, base_url: str, limit: int) -> List[str]:
    if not html or limit < 0:
        return []
    seen: dict[str, None] = {}
    for href in _FAPELLO_CONTENT_HREF_RE.findall(html):
        resolved = _abs(base_url, href)
        if resolved and resolved not in seen:
            seen[resolved] = None
        if limit > 0 and len(seen) >= limit:
            return list(seen.keys())
    for href in _FAPELLO_MEDIA_RE.findall(html):
        resolved = canonicalize_media_url(href, base_url=base_url)
        lower = resolved.lower()
        if not resolved or "favicon" in lower or "/assets/" in lower:
            continue
        if resolved not in seen:
            seen[resolved] = None
        if limit > 0 and len(seen) >= limit:
            break
    return list(seen.keys())


def is_pornpics_gallery_url(url: str) -> bool:
    if detect_creator_platform(url) != PLATFORM_PORNPICS:
        return False
    path = urlparse((url or "").strip()).path or "/"
    if path.startswith("/galleries/"):
        return True
    return bool(_PORNPICS_GALLERY_RE.match(path)) and path.strip("/") != ""


def harvest_pornpics_media(html: str, *, base_url: str, limit: int) -> List[str]:
    if not html or limit < 0:
        return []
    seen: dict[str, None] = {}
    for href in _PORNPICS_CDN_RE.findall(html):
        # Prefer larger CDN variants when the path encodes size folders.
        resolved = canonicalize_media_url(href.replace("/460/", "/1280/"))
        if resolved and resolved not in seen:
            seen[resolved] = None
        if limit > 0 and len(seen) >= limit:
            return list(seen.keys())
    for href in _PORNPICS_HREF_RE.findall(html):
        resolved = _abs(base_url, href)
        if resolved and resolved not in seen:
            seen[resolved] = None
        if limit > 0 and len(seen) >= limit:
            break
    return list(seen.keys())


def is_twpornstars_single_url(url: str) -> bool:
    if detect_creator_platform(url) != PLATFORM_TWPORNSTARS:
        return False
    path = urlparse((url or "").strip()).path or ""
    return bool(_TWPORN_VIDEO_RE.match(path))


def harvest_twpornstars_media(html: str, *, base_url: str, limit: int) -> List[str]:
    if not html or limit < 0:
        return []
    seen: dict[str, None] = {}
    for href in _TWPORN_HREF_RE.findall(html):
        resolved = _abs(base_url, href)
        if resolved and resolved not in seen:
            seen[resolved] = None
        if limit > 0 and len(seen) >= limit:
            return list(seen.keys())
    for href in _TWPORN_MEDIA_RE.findall(html):
        resolved = canonicalize_media_url(href, base_url=base_url)
        if resolved and resolved not in seen:
            seen[resolved] = None
        if limit > 0 and len(seen) >= limit:
            break
    return list(seen.keys())


# --- Resolve / rewrite / CDN download -------------------------------------------


def creator_media_id(url: str) -> Optional[str]:
    """Best-effort stable id for skip-existing filename matching."""
    platform = detect_creator_platform(url)
    text = (url or "").strip()
    if not platform or not text:
        return None
    if platform == PLATFORM_ARYION:
        return aryion_view_id(text)
    if platform == PLATFORM_CLIPS4SALE:
        _studio, clip = clips4sale_ids(text)
        return clip
    if platform == PLATFORM_MANYVIDS:
        match = re.search(r"/Video/(\d+)", text, re.IGNORECASE)
        return match.group(1) if match else None
    if platform == PLATFORM_REDGIFS:
        match = re.search(r"/watch/([A-Za-z0-9]+)", text, re.IGNORECASE)
        return match.group(1).lower() if match else None
    if platform == PLATFORM_VIMEO:
        match = re.search(r"vimeo\.com/(?:video/)?(\d+)", text, re.IGNORECASE)
        return match.group(1) if match else None
    if platform == PLATFORM_VK:
        match = re.search(r"(?:video|clip)(-?\d+_\d+)", text, re.IGNORECASE)
        return match.group(1) if match else None
    if platform == PLATFORM_REDDIT:
        match = re.search(r"/comments/([a-z0-9]+)", text, re.IGNORECASE)
        return match.group(1) if match else None
    if platform == PLATFORM_TWITTER:
        match = re.search(r"/status/(\d+)", text, re.IGNORECASE)
        return match.group(1) if match else None
    if platform == PLATFORM_TWPORNSTARS:
        match = _TWPORN_VIDEO_RE.match(urlparse(text).path or "")
        return match.group("id") if match else None
    return None


def harvest_listing(
    html: str,
    *,
    base_url: str,
    platform: str,
    limit: int,
) -> List[str]:
    if platform == PLATFORM_ARYION:
        return harvest_aryion_views(html, base_url=base_url, limit=limit)
    if platform == PLATFORM_CLIPS4SALE:
        return harvest_clips4sale_clips(html, base_url=base_url, limit=limit)
    if platform == PLATFORM_FAPELLO:
        return harvest_fapello_media(html, base_url=base_url, limit=limit)
    if platform == PLATFORM_PORNPICS:
        return harvest_pornpics_media(html, base_url=base_url, limit=limit)
    if platform == PLATFORM_TWPORNSTARS:
        return harvest_twpornstars_media(html, base_url=base_url, limit=limit)
    return []


def is_html_listing_url(url: str) -> bool:
    platform = detect_creator_platform(url)
    if platform == PLATFORM_ARYION:
        return is_aryion_listing_url(url)
    if platform == PLATFORM_CLIPS4SALE:
        return is_clips4sale_listing_url(url)
    if platform == PLATFORM_FAPELLO:
        return is_fapello_model_url(url) and not is_fapello_content_url(url)
    if platform == PLATFORM_PORNPICS:
        return is_pornpics_gallery_url(url)
    if platform == PLATFORM_TWPORNSTARS:
        return not is_twpornstars_single_url(url)
    return False


def is_html_single_url(url: str) -> bool:
    platform = detect_creator_platform(url)
    if platform == PLATFORM_ARYION:
        return is_aryion_single_url(url)
    if platform == PLATFORM_CLIPS4SALE:
        return is_clips4sale_single_url(url)
    if platform == PLATFORM_FAPELLO:
        return is_fapello_content_url(url)
    if platform == PLATFORM_TWPORNSTARS:
        return is_twpornstars_single_url(url)
    return False


def resolve_html_creator(
    url: str,
    settings: Settings,
    *,
    playlist_end: int = 100,
) -> List[str]:
    """Resolve clean-room creator hosts (singles pass through; listings harvest)."""
    input_url = canonicalize_media_url(url.strip()) or url.strip()
    platform = detect_creator_platform(input_url)
    if platform not in HTML_CREATOR_PLATFORMS:
        return [input_url]
    if is_html_single_url(input_url):
        return [input_url]
    if is_html_listing_url(input_url) or platform in HTML_CREATOR_PLATFORMS:
        html, err = fetch_html(input_url, settings)
        if err or not html:
            logging.warning("creator_media listing fetch failed %s: %s", input_url, err)
            return [input_url]
        links = harvest_listing(
            html,
            base_url=input_url,
            platform=platform,
            limit=playlist_end,
        )
        return links or [input_url]
    return [input_url]


def resolve_listing_pages(
    url: str,
    settings: Settings,
    *,
    limit: int,
    max_pages: int = 5,
    pace_seconds: float = 0.0,
    sleep_fn=None,
) -> List[str]:
    """Paced multi-page harvest for HTML creator listings (best-effort next links)."""
    import time as _time

    sleeper = sleep_fn or _time.sleep
    input_url = canonicalize_media_url(url.strip()) or url.strip()
    platform = detect_creator_platform(input_url) or ""
    seen: dict[str, None] = {}
    page_url = input_url
    pages = 0
    while page_url and pages < max(1, int(max_pages)):
        if limit > 0 and len(seen) >= limit:
            break
        if pages > 0 and pace_seconds > 0:
            sleeper(float(pace_seconds))
        html, err = fetch_html(page_url, settings)
        pages += 1
        if err or not html:
            logging.warning("creator_media page fetch failed %s: %s", page_url, err)
            break
        remaining = 0 if limit <= 0 else max(0, limit - len(seen))
        batch = harvest_listing(
            html, base_url=page_url, platform=platform, limit=remaining
        )
        for item in batch:
            if item not in seen:
                seen[item] = None
            if limit > 0 and len(seen) >= limit:
                break
        nxt = _find_next_page(html, base_url=page_url, current_url=page_url)
        if not nxt or nxt == page_url:
            break
        page_url = nxt
    return list(seen.keys())


_NEXT_HREF_RE = re.compile(
    r"""href=["']([^"']+)["'][^>]*>\s*(?:Next|»|>|Older|More)\s*<"""
    r"""|rel=["']next["'][^>]*href=["']([^"']+)["']"""
    r"""|href=["']([^"']+)["'][^>]*rel=["']next["']""",
    re.IGNORECASE,
)


def _find_next_page(html: str, *, base_url: str, current_url: str) -> Optional[str]:
    if not html:
        return None
    for match in _NEXT_HREF_RE.finditer(html):
        href = next((g for g in match.groups() if g), "")
        if not href or href.startswith("#"):
            continue
        resolved = _abs(base_url, href)
        if resolved and resolved != current_url:
            return resolved
    # Clips4Sale / Aryion page-number bump (Page2, /2/, from:2).
    parsed = urlparse(current_url)
    path = parsed.path or ""
    bumped = re.sub(
        r"(Page)(\d+)",
        lambda m: f"{m.group(1)}{int(m.group(2)) + 1}",
        path,
        count=1,
        flags=re.IGNORECASE,
    )
    if bumped != path:
        return canonicalize_media_url(
            f"{parsed.scheme}://{parsed.netloc}{bumped}"
            + (("?" + parsed.query) if parsed.query else "")
        )
    return None


def rewrite_creator_media_url(url: str, settings: Settings) -> str:
    """
    Map single item pages to direct CDN / asset URLs when yt-dlp cannot extract.

    Paid full clips stay unreachable without a purchased session; public previews
    and open gallery assets are rewritten when present in the page markup.
    """
    text = (url or "").strip()
    platform = detect_creator_platform(text)
    if platform not in HTML_CREATOR_PLATFORMS:
        return text
    if platform == PLATFORM_CLIPS4SALE and is_clips4sale_single_url(text):
        html, err = fetch_html(text, settings)
        if err or not html:
            logging.warning("clips4sale rewrite fetch failed %s: %s", text, err)
            return text
        preview = extract_clips4sale_preview_url(html)
        return preview or text
    if platform == PLATFORM_ARYION and is_aryion_single_url(text):
        # data.php serves the original upload for every item type; no need to
        # scrape derivative /g4/data/*.doc.html previews from the view page.
        media = aryion_data_php_url(text)
        if media:
            return media
        html, err = fetch_html(text, settings)
        if err or not html:
            logging.warning("aryion rewrite fetch failed %s: %s", text, err)
            return text
        return extract_aryion_media_url(html, base_url=text) or text
    if platform == PLATFORM_FAPELLO and is_fapello_content_url(text):
        html, err = fetch_html(text, settings)
        if err or not html:
            return text
        media = harvest_fapello_media(html, base_url=text, limit=1)
        return media[0] if media else text
    if platform == PLATFORM_TWPORNSTARS and is_twpornstars_single_url(text):
        html, err = fetch_html(text, settings)
        if err or not html:
            return text
        media = harvest_twpornstars_media(html, base_url=text, limit=1)
        # Prefer mp4 when present.
        for item in media:
            if re.search(r"\.(mp4|webm)(?:$|\?)", item, re.I):
                return item
        return media[0] if media else text
    if platform == PLATFORM_PORNPICS:
        # Gallery or direct CDN — harvest first large image.
        if text.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            return text
        html, err = fetch_html(text, settings)
        if err or not html:
            return text
        media = harvest_pornpics_media(html, base_url=text, limit=1)
        return media[0] if media else text
    return text


def extension_from_content_type(content_type: str) -> str:
    """Map a Content-Type header value to a dotted extension, or ''."""
    raw = (content_type or "").split(";", 1)[0].strip().lower()
    if not raw:
        return ""
    return _CONTENT_TYPE_EXTENSION.get(raw, "")


def extension_from_filename(filename: str) -> str:
    """Return a known dotted extension from a bare filename, or ''."""
    name = (filename or "").strip().strip('"').split("\\")[-1].split("/")[-1]
    if not name or "." not in name:
        return ""
    # Prefer longest known suffix (docx before doc, jpeg before …).
    lower = name.lower()
    for ext in sorted(_DIRECT_EXTENSIONS, key=len, reverse=True):
        if lower.endswith(ext):
            return ".jpg" if ext == ".jpeg" else (".html" if ext == ".htm" else ext)
    return ""


def extension_from_content_disposition(disposition: str) -> str:
    """Parse Content-Disposition filename= / filename*= for a known extension."""
    text = disposition or ""
    match = _DISPOSITION_FILENAME_RE.search(text)
    if not match:
        return ""
    raw = (match.group(1) or match.group(2) or match.group(3) or "").strip()
    if match.group(1):
        raw = unquote(raw)
    return extension_from_filename(raw)


def guess_direct_extension(
    url: str,
    default: str = ".mp4",
    *,
    content_type: str = "",
    content_disposition: str = "",
) -> str:
    """Pick a file extension from headers first, then the URL path."""
    for candidate in (
        extension_from_content_disposition(content_disposition),
        extension_from_content_type(content_type),
    ):
        if candidate:
            return candidate
    path = (urlparse(url).path or "").lower()
    # Walk path segments so /g4/data/id-hash.png/file.png and bare *.pdf work.
    for segment in reversed([p for p in path.split("/") if p]):
        ext = extension_from_filename(segment)
        if ext:
            return ext
    query = (urlparse(url).query or "").lower()
    if "data.php" in path or "id=" in query:
        return default
    return default


def download_direct_media(
    media_url: str,
    dest_path: str,
    settings: Settings,
    *,
    referer: str = "",
    progress_hook=None,
) -> Tuple[Optional[str], Optional[str]]:
    """Stream a direct CDN / asset URL to disk via yt-dlp networking.

    Returns ``(error, saved_path)``. ``saved_path`` may differ from
    ``dest_path`` when Content-Type / Content-Disposition correct the extension.
    """
    if yt_dlp is None:
        return "yt-dlp is not installed", None
    text = canonicalize_media_url(media_url)
    if not text:
        return "empty media url", None
    ydl_opts = apply_auth_opts({"quiet": True, "noprogress": True}, settings)
    headers = dict(ydl_opts.get("http_headers") or {})
    if referer:
        headers["Referer"] = referer
    if headers:
        ydl_opts["http_headers"] = headers
    saved = dest_path
    try:
        parent = os.path.dirname(dest_path) or "."
        os.makedirs(parent, exist_ok=True)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            resp = ydl.urlopen(text)
            ctype = resp.headers.get("Content-Type") or ""
            cdisp = resp.headers.get("Content-Disposition") or ""
            corrected = guess_direct_extension(
                text,
                default=os.path.splitext(dest_path)[1] or ".bin",
                content_type=ctype,
                content_disposition=cdisp,
            )
            base, cur_ext = os.path.splitext(dest_path)
            if corrected and corrected.lower() != (cur_ext or "").lower():
                saved = base + corrected
            total = 0
            expected = None
            try:
                expected = int(resp.headers.get("Content-Length") or 0) or None
            except (TypeError, ValueError):
                expected = None
            with open(saved, "wb") as handle:
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    total += len(chunk)
                    if progress_hook:
                        progress_hook(
                            {
                                "status": "downloading",
                                "downloaded_bytes": total,
                                "total_bytes": expected,
                                "filename": saved,
                            }
                        )
        if progress_hook:
            progress_hook(
                {
                    "status": "finished",
                    "downloaded_bytes": total,
                    "total_bytes": expected or total,
                    "filename": saved,
                }
            )
        if saved != dest_path and os.path.isfile(dest_path):
            try:
                os.remove(dest_path)
            except OSError:
                pass
    except Exception as error:
        return str(error), None
    return None, saved


def safe_title_for_url(url: str, html: str = "") -> str:
    title = extract_page_title(html) if html else ""
    if title:
        return clean_filename(title) or title
    media_id = creator_media_id(url) or "media"
    platform = detect_creator_platform(url) or "creator"
    return clean_filename(f"{platform}_{media_id}") or f"{platform}_{media_id}"


def media_payload_mismatches_extension(path: str) -> bool:
    """True when on-disk magic clearly disagrees with the file extension.

    Used so skip-existing does not keep Aryion HTML/PDF payloads saved as ``.mp4``.
    """
    if not path or not os.path.isfile(path):
        return False
    ext = os.path.splitext(path)[1].lower()
    try:
        with open(path, "rb") as handle:
            head = handle.read(64)
    except OSError:
        return False
    if not head:
        return True
    stripped = head.lstrip()
    is_html = stripped[:15].lower().startswith(b"<!doctype html") or stripped[
        :6
    ].lower().startswith(b"<html")
    is_pdf = head.startswith(b"%PDF")
    is_png = head.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpeg = head.startswith(b"\xff\xd8\xff")
    is_gif = head.startswith(b"GIF87a") or head.startswith(b"GIF89a")
    is_zip = head.startswith(b"PK\x03\x04")  # docx/xlsx/zip
    is_ole = head.startswith(b"\xd0\xcf\x11\xe0")  # legacy .doc
    is_mp4 = b"ftyp" in head[4:12]
    is_swf = head[:3] in (b"FWS", b"CWS", b"ZWS")
    if is_html and ext not in (".html", ".htm"):
        return True
    if is_pdf and ext != ".pdf":
        return True
    if is_png and ext != ".png":
        return True
    if is_jpeg and ext not in (".jpg", ".jpeg"):
        return True
    if is_gif and ext != ".gif":
        return True
    if is_mp4 and ext not in (".mp4", ".m4v", ".mov", ".m4a"):
        return True
    if is_swf and ext != ".swf":
        return True
    if is_ole and ext != ".doc":
        return True
    if is_zip and ext in (".mp4", ".png", ".jpg", ".jpeg", ".gif", ".webm", ".pdf", ".html", ".htm", ".txt"):
        # ZIP container saved under a media/doc-preview extension → likely docx etc.
        return True
    return False


def needs_direct_cdn_download(original_url: str, download_url: str) -> bool:
    """True when download_url is a rewritten direct asset (not the page URL)."""
    if not download_url or download_url == original_url:
        return False
    platform = detect_creator_platform(original_url)
    if platform not in HTML_CREATOR_PLATFORMS:
        return False
    lower = download_url.lower()
    if any(
        marker in lower
        for marker in (
            "clips_previews/",
            "/g4/data/",
            "data.php",
            "cdni.pornpics.com",
            ".mp4",
            ".webm",
            ".jpg",
            ".png",
            ".webp",
            ".gif",
            ".pdf",
            ".swf",
            ".doc",
            ".zip",
        )
    ):
        return True
    return download_url != original_url
