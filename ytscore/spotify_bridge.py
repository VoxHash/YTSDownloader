"""Spotify metadata bridge using the local desktop session (MPRIS) and URL parsing.

Does not stream Spotify audio. Resolves track/playlist metadata, then matches
public media hosts via search for download.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from ytscore.settings import Settings, apply_auth_opts

try:
    import yt_dlp
except ImportError:  # pragma: no cover
    yt_dlp = None

MPRIS_NAME = "org.mpris.MediaPlayer2.spotify"
MPRIS_PATH = "/org/mpris/MediaPlayer2"
SPOTIFY_TRACK_RE = re.compile(
    r"(?:open\.spotify\.com/track/|spotify:track:)([A-Za-z0-9]+)"
)
SPOTIFY_PLAYLIST_RE = re.compile(
    r"(?:open\.spotify\.com/playlist/|spotify:playlist:)([A-Za-z0-9]+)"
)
SPOTIFY_ALBUM_RE = re.compile(
    r"(?:open\.spotify\.com/album/|spotify:album:)([A-Za-z0-9]+)"
)


@dataclass
class TrackMeta:
    title: str
    artists: List[str]
    album: str = ""
    spotify_url: str = ""
    track_id: str = ""
    art_url: str = ""
    source: str = "unknown"

    @property
    def search_query(self) -> str:
        artist = ", ".join(self.artists) if self.artists else ""
        if artist and self.title:
            return f"{artist} - {self.title}"
        return self.title or artist or self.spotify_url


def session_available() -> bool:
    try:
        read_now_playing()
        return True
    except Exception:
        return False


def read_now_playing() -> TrackMeta:
    """Read currently playing track from the local Spotify MPRIS session (Linux)."""
    errors = []
    for reader in (_read_mpris_dbus_send, _read_mpris_busctl, _read_mpris_gi):
        try:
            return reader()
        except Exception as exc:
            errors.append(f"{reader.__name__}: {exc}")
    raise RuntimeError(
        "Spotify MPRIS session unavailable. Open the Spotify desktop client and play a track. "
        + " | ".join(errors)
    )


def _read_mpris_dbus_send() -> TrackMeta:
    proc = subprocess.run(
        [
            "dbus-send",
            "--print-reply",
            f"--dest={MPRIS_NAME}",
            MPRIS_PATH,
            "org.freedesktop.DBus.Properties.Get",
            "string:org.mpris.MediaPlayer2.Player",
            "string:Metadata",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "dbus-send failed")
    return _parse_dbus_send_metadata(proc.stdout)


def _read_mpris_busctl() -> TrackMeta:
    proc = subprocess.run(
        [
            "busctl",
            "--user",
            "get-property",
            MPRIS_NAME,
            MPRIS_PATH,
            "org.mpris.MediaPlayer2.Player",
            "Metadata",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "busctl failed")
    return _parse_busctl_metadata(proc.stdout)


def _read_mpris_gi() -> TrackMeta:
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio

    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    props = Gio.DBusProxy.new_sync(
        bus,
        Gio.DBusProxyFlags.NONE,
        None,
        MPRIS_NAME,
        MPRIS_PATH,
        "org.freedesktop.DBus.Properties",
        None,
    )
    meta = dict(props.Get("(ss)", "org.mpris.MediaPlayer2.Player", "Metadata"))
    return _track_from_mapping(meta)


def _track_from_mapping(meta: dict) -> TrackMeta:
    title = str(meta.get("xesam:title") or "")
    album = str(meta.get("xesam:album") or "")
    art = str(meta.get("mpris:artUrl") or "")
    url = str(meta.get("xesam:url") or "")
    artists_raw = meta.get("xesam:artist") or []
    if isinstance(artists_raw, (list, tuple)):
        artists = [str(a) for a in artists_raw]
    else:
        artists = [str(artists_raw)] if artists_raw else []
    track_id = ""
    m = SPOTIFY_TRACK_RE.search(url)
    if m:
        track_id = m.group(1)
    if not title and not artists:
        raise RuntimeError("Spotify is open but no track metadata is available yet.")
    return TrackMeta(
        title=title,
        artists=artists,
        album=album,
        spotify_url=url,
        track_id=track_id,
        art_url=art,
        source="mpris",
    )


def _parse_dbus_send_metadata(text: str) -> TrackMeta:
    """Parse dbus-send --print-reply Metadata variant."""
    title = _dbus_string_after(text, "xesam:title")
    album = _dbus_string_after(text, "xesam:album") or ""
    url = _dbus_string_after(text, "xesam:url") or ""
    art = _dbus_string_after(text, "mpris:artUrl") or ""
    artists = _dbus_string_array_after(text, "xesam:artist")
    return _track_from_mapping(
        {
            "xesam:title": title,
            "xesam:album": album,
            "xesam:url": url,
            "mpris:artUrl": art,
            "xesam:artist": artists,
        }
    )


def _dbus_string_after(text: str, key: str) -> str:
    # dict entry( string "key" variant string "value" )
    pattern = rf'string\s+"{re.escape(key)}"\s+variant\s+string\s+"(.*?)"'
    m = re.search(pattern, text, re.DOTALL)
    if not m:
        return ""
    return _unescape_dbus_string(m.group(1))


def _dbus_string_array_after(text: str, key: str) -> List[str]:
    pattern = rf'string\s+"{re.escape(key)}"\s+variant\s+array\s*\[\s*(.*?)\s*\]'
    m = re.search(pattern, text, re.DOTALL)
    if not m:
        return []
    return [
        _unescape_dbus_string(s)
        for s in re.findall(r'string\s+"(.*?)"', m.group(1), re.DOTALL)
    ]


def _unescape_dbus_string(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )


def _parse_busctl_metadata(text: str) -> TrackMeta:
    # Example fragment: "xesam:title" s "Song" "xesam:artist" as 1 "Artist"
    title_m = re.search(r'"xesam:title"\s+s\s+"(.*?)"', text)
    album_m = re.search(r'"xesam:album"\s+s\s+"(.*?)"', text)
    url_m = re.search(r'"xesam:url"\s+s\s+"(.*?)"', text)
    art_m = re.search(r'"mpris:artUrl"\s+s\s+"(.*?)"', text)
    artists: List[str] = []
    artist_block = re.search(r'"xesam:artist"\s+as\s+\d+\s+(.*?)(?="xesam:|"mpris:|$)', text)
    if artist_block:
        artists = re.findall(r'"([^"]+)"', artist_block.group(1))
    return _track_from_mapping(
        {
            "xesam:title": title_m.group(1) if title_m else "",
            "xesam:album": album_m.group(1) if album_m else "",
            "xesam:url": url_m.group(1) if url_m else "",
            "mpris:artUrl": art_m.group(1) if art_m else "",
            "xesam:artist": artists,
        }
    )


def parse_spotify_url(url: str) -> Optional[str]:
    """Return kind: track | playlist | album | None."""
    if SPOTIFY_TRACK_RE.search(url):
        return "track"
    if SPOTIFY_PLAYLIST_RE.search(url):
        return "playlist"
    if SPOTIFY_ALBUM_RE.search(url):
        return "album"
    host = (urlparse(url).hostname or "").lower()
    if "spotify" in host:
        return "unknown"
    return None


def resolve_spotify_entries(url: str, settings: Settings) -> List[TrackMeta]:
    """Resolve Spotify open URLs to track metadata."""
    kind = parse_spotify_url(url)
    if kind is None:
        return []

    track_m = SPOTIFY_TRACK_RE.search(url)
    if kind == "track" and track_m:
        tid = track_m.group(1)
        try:
            now = read_now_playing()
            if now.track_id == tid:
                return [now]
        except Exception:
            pass
        meta = _extract_spotify_via_ytdlp(url, settings)
        if meta:
            return meta
        return [
            TrackMeta(
                title=tid,
                artists=[],
                spotify_url=f"https://open.spotify.com/track/{tid}",
                track_id=tid,
                source="url",
            )
        ]

    return _extract_spotify_via_ytdlp(url, settings)


def _extract_spotify_via_ytdlp(url: str, settings: Settings) -> List[TrackMeta]:
    if yt_dlp is None:
        return []
    ydl_opts = apply_auth_opts(
        {"quiet": True, "extract_flat": True, "skip_download": True},
        settings,
    )
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        logging.warning("Catalog URL extract failed: %s", exc)
        return []

    tracks: List[TrackMeta] = []
    entries = None
    if isinstance(info, dict):
        entries = info.get("entries")
        if not entries:
            entries = [info]
    for entry in entries or []:
        if not entry:
            continue
        title = entry.get("track") or entry.get("title") or ""
        artist = entry.get("artist") or entry.get("uploader") or ""
        artists = [artist] if isinstance(artist, str) and artist else list(artist or [])
        album = entry.get("album") or ""
        webpage = entry.get("webpage_url") or entry.get("url") or url
        tid = ""
        m = SPOTIFY_TRACK_RE.search(str(webpage))
        if m:
            tid = m.group(1)
        if not title and not artists:
            continue
        tracks.append(
            TrackMeta(
                title=str(title),
                artists=[str(a) for a in artists] if artists else [],
                album=str(album),
                spotify_url=str(webpage),
                track_id=tid,
                source="extractor",
            )
        )
    return tracks


def tracks_to_search_jobs(tracks: List[TrackMeta]) -> List[tuple]:
    """Return list of (display_title, search_query, spotify_url)."""
    out = []
    for t in tracks:
        q = t.search_query.strip()
        if not q:
            continue
        out.append((q, q, t.spotify_url))
    return out
