"""URL / playlist / channel / profile resolvers via yt-dlp."""

from __future__ import annotations

import logging
from typing import List, Sequence
from urllib.parse import urlparse

from ytscore.cache import title_cache
from ytscore.settings import Settings, apply_auth_opts

try:
    import yt_dlp
except ImportError:  # pragma: no cover
    yt_dlp = None


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
    return "generic"


def resolve_youtube(url: str, settings: Settings, playlist_end: int = 100) -> List[str]:
    yt_dlp = _require_yt_dlp()
    input_url = url.strip()
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

    ydl_opts = apply_auth_opts(
        {"quiet": True, "extract_flat": True, "playlist_end": playlist_end},
        settings,
    )
    links: List[str] = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for tab_path in ("/videos", "/shorts"):
            try:
                result = ydl.extract_info(f"{channel_url}{tab_path}", download=False)
            except Exception as error:
                logging.warning("Could not extract %s%s: %s", channel_url, tab_path, error)
                continue
            if not isinstance(result, dict) or "entries" not in result:
                continue
            for entry in result["entries"] or []:
                if not entry:
                    continue
                entry_url = entry.get("url") or entry.get("webpage_url")
                entry_id = entry.get("id")
                entry_title = entry.get("title")
                if entry_url and str(entry_url).startswith("http"):
                    links.append(entry_url)
                    title_cache.put(entry_url, entry_title)
                elif entry_id:
                    resolved = f"https://www.youtube.com/watch?v={entry_id}"
                    links.append(resolved)
                    title_cache.put(resolved, entry_title)

    if not links:
        # Fallback: treat as playlist / single extract
        return resolve_flat(input_url, settings, playlist_end=playlist_end)
    return list(dict.fromkeys(links))


def resolve_flat(url: str, settings: Settings, playlist_end: int = 100) -> List[str]:
    yt_dlp = _require_yt_dlp()
    input_url = url.strip()
    ydl_opts = apply_auth_opts(
        {"quiet": True, "extract_flat": True, "playlist_end": playlist_end},
        settings,
    )
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
            if not entry:
                continue
            entry_url = entry.get("url") or entry.get("webpage_url")
            entry_title = entry.get("title")
            if entry_url and str(entry_url).startswith("http"):
                links.append(entry_url)
                title_cache.put(entry_url, entry_title)
        if links:
            return list(dict.fromkeys(links))
    return [input_url]


def resolve_url(url: str, settings: Settings, playlist_end: int = 100) -> List[str]:
    platform = detect_platform(url)
    if platform == "youtube":
        return resolve_youtube(url, settings, playlist_end=playlist_end)
    if platform == "spotify":
        return [url.strip()]
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
        ydl.extract_info(url.strip(), download=False)
