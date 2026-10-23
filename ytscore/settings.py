"""Load and expose application settings from config.ini."""

from __future__ import annotations

import configparser
import os
import tempfile
from dataclasses import dataclass
from typing import Optional, Tuple

DEFAULT_CONFIG_PATH = "config.ini"


@dataclass
class Settings:
    theme: str = "SuiteDark"
    pace_seconds: float = 2.5
    cookies_from_browser: str = ""
    cookies_file: str = ""
    js_runtime: str = ""
    js_runtime_path: str = ""
    max_workers: int = 2
    max_retries: int = 3
    default_output: str = ""
    audio_format: str = "m4a"
    video_format_pref: str = "bestvideo+bestaudio/best"
    # Exponential backoff between download retries (and harder on HTTP 429).
    backoff_base: float = 2.0
    backoff_factor: float = 2.0
    backoff_max: float = 90.0

    def cookies_tuple(self) -> Optional[Tuple[str, ...]]:
        parts = [p.strip() for p in self.cookies_from_browser.split(":") if p.strip()]
        return tuple(parts) if parts else None


def load_settings(path: str = DEFAULT_CONFIG_PATH) -> Settings:
    cfg = configparser.ConfigParser()
    if not os.path.isfile(path):
        return Settings()
    cfg.read(path)
    s = cfg["SETTINGS"] if cfg.has_section("SETTINGS") else {}
    return Settings(
        theme=s.get("THEME", "SuiteDark"),
        pace_seconds=float(s.get("COUNT_TIMER_ONGOING", "2.5")),
        cookies_from_browser=s.get("COOKIES_FROM_BROWSER", "").strip(),
        cookies_file=s.get("COOKIES_FILE", "").strip(),
        js_runtime=s.get("JS_RUNTIME", "").strip(),
        js_runtime_path=s.get("JS_RUNTIME_PATH", "").strip(),
        max_workers=max(1, int(s.get("MAX_WORKERS", "2"))),
        max_retries=max(0, int(s.get("MAX_RETRIES", "3"))),
        default_output=s.get("DEFAULT_OUTPUT", "").strip(),
        audio_format=s.get("AUDIO_FORMAT", "m4a").strip() or "m4a",
        video_format_pref=s.get("VIDEO_FORMAT", "bestvideo+bestaudio/best").strip()
        or "bestvideo+bestaudio/best",
        backoff_base=max(0.0, float(s.get("BACKOFF_BASE", "2"))),
        backoff_factor=max(1.0, float(s.get("BACKOFF_FACTOR", "2"))),
        backoff_max=max(0.0, float(s.get("BACKOFF_MAX", "90"))),
    )


def save_settings(settings: Settings, path: str = DEFAULT_CONFIG_PATH) -> None:
    """Write Settings to config.ini under [SETTINGS], atomically replacing the file."""
    cfg = configparser.ConfigParser()
    if os.path.isfile(path):
        cfg.read(path)
    if not cfg.has_section("SETTINGS"):
        cfg.add_section("SETTINGS")
    s = cfg["SETTINGS"]
    s["THEME"] = (settings.theme or "SuiteDark").strip() or "SuiteDark"
    s["COUNT_TIMER_ONGOING"] = str(float(settings.pace_seconds))
    s["COOKIES_FROM_BROWSER"] = (settings.cookies_from_browser or "").strip()
    s["COOKIES_FILE"] = (settings.cookies_file or "").strip()
    s["JS_RUNTIME"] = (settings.js_runtime or "").strip()
    s["JS_RUNTIME_PATH"] = (settings.js_runtime_path or "").strip()
    s["MAX_WORKERS"] = str(max(1, int(settings.max_workers)))
    s["MAX_RETRIES"] = str(max(0, int(settings.max_retries)))
    s["BACKOFF_BASE"] = str(max(0.0, float(settings.backoff_base)))
    s["BACKOFF_FACTOR"] = str(max(1.0, float(settings.backoff_factor)))
    s["BACKOFF_MAX"] = str(max(0.0, float(settings.backoff_max)))
    s["AUDIO_FORMAT"] = (settings.audio_format or "m4a").strip() or "m4a"
    s["VIDEO_FORMAT"] = (
        (settings.video_format_pref or "bestvideo+bestaudio/best").strip()
        or "bestvideo+bestaudio/best"
    )
    s["DEFAULT_OUTPUT"] = (settings.default_output or "").strip()

    abs_path = os.path.abspath(path)
    directory = os.path.dirname(abs_path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".config-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            cfg.write(fh)
        os.replace(tmp, abs_path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def apply_auth_opts(ydl_opts: dict, settings: Settings) -> dict:
    ydl_opts = dict(ydl_opts)
    ydl_opts["no_color"] = True
    # Allow fetching the external JS challenge solver used by modern extractors.
    ydl_opts.setdefault("remote_components", {"ejs:github"})
    if settings.js_runtime:
        if settings.js_runtime_path:
            ydl_opts["js_runtimes"] = {settings.js_runtime: {"path": settings.js_runtime_path}}
        else:
            ydl_opts["js_runtimes"] = {settings.js_runtime: {}}
    cookies = settings.cookies_tuple()
    if cookies:
        ydl_opts["cookiesfrombrowser"] = cookies
    elif settings.cookies_file:
        ydl_opts["cookiefile"] = settings.cookies_file
    return ydl_opts
