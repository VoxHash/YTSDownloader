"""Clean-room helpers for the rule34video.com adult video host class.

Uses Suite auth (yt-dlp networking + cookies + TLS impersonation) and HTML
harvest for listing / tag / member / search pages. Single-video pages are
rewritten to direct ``get_file`` CDN URLs when the stock yt-dlp extractor
misses formats (download-sheet markup drift). Does not vendor third-party
userscripts; only surfaces the signed-in session can already open.
"""

from __future__ import annotations

import logging
import os
import re
from typing import List, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlparse

from ytscore.settings import Settings, apply_auth_opts
from ytscore.util import canonicalize_media_url

try:
    import yt_dlp
except ImportError:  # pragma: no cover
    yt_dlp = None

PLATFORM_ID = "rule34_video"

_HOST_MARKERS = ("rule34video.com",)

_VIDEO_PATH_RE = re.compile(
    r"^/videos?/(?P<id>\d+)(?:/|$)",
    re.IGNORECASE,
)
_MEMBER_PATH_RE = re.compile(
    r"^/(?:members|users|profile)/(?P<id>\d+)(?:/|$)",
    re.IGNORECASE,
)
_TAG_PATH_RE = re.compile(r"^/tags/(?P<id>\d+)(?:/|$)", re.IGNORECASE)
_CATEGORY_PATH_RE = re.compile(
    r"^/categories/(?P<slug>[^/?#]+)(?:/|$)",
    re.IGNORECASE,
)
_SEARCH_PATH_RE = re.compile(r"^/search/?", re.IGNORECASE)
_LISTING_ROOTS = (
    "/latest-updates",
    "/top-rated",
    "/most-popular",
    "/longest",
)

_HREF_VIDEO_RE = re.compile(
    r"""href=["']([^"']*/videos?/\d+/[^"']*)["']""",
    re.IGNORECASE,
)
_DOWNLOAD_TRUE_RE = re.compile(
    r"""href=["']([^"']*download=true[^"']*)["']""",
    re.IGNORECASE,
)
_FLASHVAR_URL_RE = re.compile(
    r"""(?:video_url|video_alt_url\d*)\s*:\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)
_FLASHVAR_TEXT_RE = re.compile(
    r"""(?:video_url_text|video_alt_url\d*_text)\s*:\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)
_QUALITY_IN_URL_RE = re.compile(r"[_\-/](\d{3,4})p?(?:[_\-./?]|$)", re.IGNORECASE)
_NEXT_PAGE_HREF_RE = re.compile(
    r"""href=["']([^"']+)["'][^>]*data-parameters=["'][^"']*from[_:]?\w*\s*:\s*0*(\d+)""",
    re.IGNORECASE,
)
_TRAILING_PAGE_RE = re.compile(r"/(\d{1,6})/?$")


def is_rule34_video_host(url: str) -> bool:
    host = (urlparse((url or "").strip()).hostname or "").lower()
    return any(marker in host for marker in _HOST_MARKERS)


def rule34_video_id(url: str) -> Optional[str]:
    path = urlparse((url or "").strip()).path or ""
    match = _VIDEO_PATH_RE.match(path)
    return match.group("id") if match else None


def is_rule34_video_single_url(url: str) -> bool:
    return rule34_video_id(url) is not None


def is_rule34_video_listing_url(url: str) -> bool:
    """True for tag / member / search / category / feed listing pages."""
    text = (url or "").strip()
    if not text or not is_rule34_video_host(text) or is_rule34_video_single_url(text):
        return False
    parsed = urlparse(text)
    path = parsed.path or "/"
    if _MEMBER_PATH_RE.match(path):
        return True
    if _TAG_PATH_RE.match(path):
        return True
    if _CATEGORY_PATH_RE.match(path):
        return True
    if _SEARCH_PATH_RE.match(path) or "q=" in (parsed.query or "").lower():
        return True
    lowered = path.rstrip("/").lower()
    for root in _LISTING_ROOTS:
        if lowered == root or lowered.startswith(root + "/"):
            return True
    return False


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


def _quality_height(label: str) -> int:
    text = (label or "").strip().lower()
    if text in ("8k", "4320", "4320p"):
        return 4320
    if text in ("4k", "2160", "2160p"):
        return 2160
    match = re.search(r"(\d{3,4})", text)
    return int(match.group(1)) if match else 0


def _quality_from_url(url: str) -> int:
    match = _QUALITY_IN_URL_RE.search(url or "")
    if not match:
        return 0
    return int(match.group(1))


def harvest_listing_videos(
    html: str,
    *,
    base_url: str,
    limit: int,
) -> List[str]:
    """Extract ``/video/<id>/…`` page URLs from a listing HTML document."""
    if not html or limit < 0:
        return []
    seen: dict[str, None] = {}
    host_base = canonicalize_media_url(base_url) or base_url

    def _budget_full() -> bool:
        return limit > 0 and len(seen) >= limit

    for href in _HREF_VIDEO_RE.findall(html):
        if _budget_full():
            break
        cleaned = canonicalize_media_url(urljoin(host_base, href), base_url=host_base)
        if not cleaned.startswith("http"):
            continue
        if not is_rule34_video_single_url(cleaned):
            continue
        if cleaned not in seen:
            seen[cleaned] = None
    return list(seen.keys())


def _listing_page_number(url: str) -> int:
    """Infer 1-based page index from common listing URL shapes."""
    path = urlparse((url or "").strip()).path or "/"
    lowered = path.rstrip("/").lower()
    for root in _LISTING_ROOTS:
        if lowered == root:
            return 1
        if lowered.startswith(root + "/"):
            m = _TRAILING_PAGE_RE.search(lowered)
            return int(m.group(1)) if m else 1
    parts = [p for p in path.split("/") if p]
    if (
        len(parts) >= 3
        and parts[0].lower() in ("tags", "members", "users", "categories")
        and parts[-1].isdigit()
        and parts[1].isdigit()
        and parts[-1] != parts[1]
    ):
        return int(parts[-1])
    return 1


def find_next_listing_page(html: str, *, base_url: str, current_url: str) -> Optional[str]:
    """
    Pick the next listing page href when pagination is present.

    Prefers numeric ``/path/N/`` links and ``data-parameters`` ``from:`` markers.
    """
    if not html:
        return None
    host_base = canonicalize_media_url(base_url) or base_url
    current = canonicalize_media_url(current_url) or current_url
    current_page = _listing_page_number(current)

    candidates: List[Tuple[int, str]] = []
    for href, from_num in _NEXT_PAGE_HREF_RE.findall(html):
        cleaned = canonicalize_media_url(urljoin(host_base, href), base_url=host_base)
        if cleaned.startswith("http"):
            candidates.append((int(from_num), cleaned))

    for href in re.findall(r"""href=["']([^"']+)["']""", html, re.IGNORECASE):
        cleaned = canonicalize_media_url(urljoin(host_base, href), base_url=host_base)
        if not cleaned.startswith("http") or cleaned == current:
            continue
        page_num = _listing_page_number(cleaned)
        path = urlparse(cleaned).path or ""
        lowered = path.rstrip("/").lower()
        is_feed = any(
            lowered == root or lowered.startswith(root + "/") for root in _LISTING_ROOTS
        )
        parts = [p for p in path.split("/") if p]
        is_tagged = (
            len(parts) >= 3
            and parts[0].lower() in ("tags", "members", "users", "categories")
            and parts[-1].isdigit()
            and parts[1].isdigit()
            and parts[-1] != parts[1]
        )
        if is_feed or is_tagged:
            candidates.append((page_num, cleaned))

    ahead = sorted(
        ((n, u) for n, u in candidates if n > current_page and u != current),
        key=lambda item: item[0],
    )
    if ahead:
        return ahead[0][1]
    return None


def extract_media_formats(html: str, *, base_url: str = "") -> List[dict]:
    """
    Parse quality-labelled direct media URLs from flashvars + download sheet.

    Returns dicts with ``url`` and ``height`` (0 when unknown), best first.
    """
    if not html:
        return []
    host_base = canonicalize_media_url(base_url) or base_url or "https://rule34video.com/"
    formats: List[dict] = []
    seen: set[str] = set()

    def _add(raw: str, height_hint: int = 0) -> None:
        cleaned = canonicalize_media_url(urljoin(host_base, raw), base_url=host_base)
        if not cleaned.startswith("http") or cleaned in seen:
            return
        if "get_file/" not in cleaned and "download=true" not in cleaned.lower():
            # Still accept get_file-less download=true sheet links.
            if "download=true" not in cleaned.lower():
                return
        seen.add(cleaned)
        height = height_hint or _quality_from_url(cleaned)
        formats.append({"url": cleaned, "height": height})

    flash_urls = _FLASHVAR_URL_RE.findall(html)
    flash_texts = _FLASHVAR_TEXT_RE.findall(html)
    for i, raw in enumerate(flash_urls):
        hint = _quality_height(flash_texts[i]) if i < len(flash_texts) else 0
        _add(raw, hint)

    for raw in _DOWNLOAD_TRUE_RE.findall(html):
        _add(raw, _quality_from_url(raw))

    formats.sort(key=lambda item: (-int(item.get("height") or 0), item["url"]))
    # Deduplicate by height keeping first (best URL).
    best_by_height: dict[int, dict] = {}
    ordered: List[dict] = []
    for item in formats:
        h = int(item.get("height") or 0)
        if h and h in best_by_height:
            continue
        if h:
            best_by_height[h] = item
        ordered.append(item)
    return ordered


def normalize_cdn_media_url(url: str) -> str:
    """
    Fix CDN quirks that break yt-dlp extension sniffing.

    ``…/file.mp4/?token=…`` → ``…/file.mp4?token=…`` so the extractor keeps
    ``mp4`` instead of treating a slash/redirect as an unsafe ``php`` path.
    """
    text = (url or "").strip()
    if not text:
        return text
    # Collapse ".mp4/" (and webm/m4v) immediately before "?" or end.
    text = re.sub(
        r"\.(mp4|webm|m4v|mov)/(\?|$)",
        r".\1\2",
        text,
        flags=re.IGNORECASE,
    )
    return text


def select_best_media_url(formats: Sequence[dict], *, prefer_height: int = 0) -> str:
    """Pick a direct media URL. ``prefer_height`` > 0 selects closest without going under when possible."""
    if not formats:
        return ""
    if prefer_height > 0:
        at_or_below = [f for f in formats if int(f.get("height") or 0) <= prefer_height]
        if at_or_below:
            at_or_below.sort(key=lambda f: -int(f.get("height") or 0))
            return normalize_cdn_media_url(str(at_or_below[0]["url"]))
    return normalize_cdn_media_url(str(formats[0]["url"]))


def extract_page_title(html: str) -> str:
    """Best-effort title from a video page document."""
    if not html:
        return ""
    for pattern in (
        r"""property=["']og:title["'][^>]*content=["']([^"']+)["']""",
        r"""content=["']([^"']+)["'][^>]*property=["']og:title["']""",
        r"<title[^>]*>([^<]+)</title>",
        r"""video_title\s*:\s*['"]([^'"]+)['"]""",
    ):
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            title = re.sub(r"\s*-\s*Rule34Video\s*$", "", match.group(1), flags=re.I)
            title = re.sub(r"\s+", " ", title).strip()
            if title:
                return title
    return ""


def resolve_video_media_url(url: str, settings: Settings) -> Optional[str]:
    """Fetch a single video page and return the best direct ``get_file`` URL."""
    if not is_rule34_video_single_url(url):
        return None
    html, err = fetch_html(url, settings)
    if err or not html:
        logging.warning("rule34_video page fetch failed %s: %s", url, err)
        return None
    formats = extract_media_formats(html, base_url=url)
    media = select_best_media_url(formats)
    return media or None


def prepare_cdn_download_url(media_url: str, *, filename: str = "video.mp4") -> str:
    """Attach download hints the CDN accepts for Content-Disposition."""
    text = normalize_cdn_media_url(media_url)
    if not text:
        return text
    if "download=true" not in text.lower():
        sep = "&" if "?" in text else "?"
        safe_name = re.sub(r"[^\w.\-]+", "_", filename)[:120] or "video.mp4"
        if not re.search(r"\.(mp4|webm|m4v|mov)$", safe_name, re.I):
            safe_name = f"{safe_name}.mp4"
        text = f"{text}{sep}download=true&download_filename={safe_name}"
    return text


def download_cdn_media(
    media_url: str,
    dest_path: str,
    settings: Settings,
    *,
    referer: str = "",
    progress_hook=None,
) -> Optional[str]:
    """
    Stream a get_file CDN URL to disk via yt-dlp networking.

    The CDN redirects through a ``.php`` endpoint that yt-dlp refuses to save
    (unsafe extension). Direct streaming keeps cookies / impersonate and writes
    a real ``.mp4``.
    """
    if yt_dlp is None:
        return "yt-dlp is not installed"
    text = prepare_cdn_download_url(media_url)
    if not text:
        return "empty media url"
    ydl_opts = apply_auth_opts({"quiet": True, "noprogress": True}, settings)
    headers = dict(ydl_opts.get("http_headers") or {})
    if referer:
        headers["Referer"] = referer
    if headers:
        ydl_opts["http_headers"] = headers
    try:
        parent = os.path.dirname(dest_path) or "."
        os.makedirs(parent, exist_ok=True)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            resp = ydl.urlopen(text)
            total = 0
            expected = None
            try:
                expected = int(resp.headers.get("Content-Length") or 0) or None
            except (TypeError, ValueError):
                expected = None
            with open(dest_path, "wb") as handle:
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
                                "filename": dest_path,
                            }
                        )
        if progress_hook:
            progress_hook(
                {
                    "status": "finished",
                    "downloaded_bytes": total,
                    "total_bytes": expected or total,
                    "filename": dest_path,
                }
            )
    except Exception as error:
        return str(error)
    return None


def rewrite_rule34_video_media_url(url: str, settings: Settings) -> str:
    """
    Map video page URLs to a direct CDN media URL for download.

    Listing URLs are returned unchanged (expand at crawl/resolve time).
    """
    text = (url or "").strip()
    if not text or not is_rule34_video_host(text):
        return text
    if is_rule34_video_single_url(text):
        media = resolve_video_media_url(text, settings)
        if media:
            return media
    return text


def resolve_listing_pages(
    url: str,
    settings: Settings,
    *,
    limit: int,
    max_pages: int = 10,
    pace_seconds: float = 0.0,
    sleep_fn=None,
) -> List[str]:
    """
    Harvest video page URLs across listing pagination (paced).

    ``limit`` ``0`` = unlimited (still capped by ``max_pages``).
    """
    import time as _time

    sleeper = sleep_fn or _time.sleep
    input_url = canonicalize_media_url(url.strip()) or url.strip()
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
            logging.warning("rule34_video listing fetch failed %s: %s", page_url, err)
            break
        remaining = 0 if limit <= 0 else max(0, limit - len(seen))
        batch = harvest_listing_videos(html, base_url=page_url, limit=remaining)
        for item in batch:
            if item not in seen:
                seen[item] = None
            if limit > 0 and len(seen) >= limit:
                break
        if limit > 0 and len(seen) >= limit:
            break
        nxt = find_next_listing_page(html, base_url=page_url, current_url=page_url)
        if not nxt or nxt == page_url:
            break
        page_url = nxt
    return list(seen.keys())
