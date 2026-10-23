"""Load and expose application settings from config.ini."""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Settings:
    theme: str = "SuiteDark"
    pace_seconds: float = 2.0
    cookies_from_browser: str = ""
    cookies_file: str = ""
    js_runtime: str = ""
    js_runtime_path: str = ""
    max_workers: int = 2
    max_retries: int = 3
    default_output: str = ""
    audio_format: str = "m4a"
    video_format_pref: str = "bestvideo+bestaudio/best"

    def cookies_tuple(self) -> Optional[Tuple[str, ...]]:
        parts = [p.strip() for p in self.cookies_from_browser.split(":") if p.strip()]
        return tuple(parts) if parts else None


def load_settings(path: str = "config.ini") -> Settings:
    cfg = configparser.ConfigParser()
    if not os.path.isfile(path):
        return Settings()
    cfg.read(path)
    s = cfg["SETTINGS"] if cfg.has_section("SETTINGS") else {}
    return Settings(
        theme=s.get("THEME", "SuiteDark"),
        pace_seconds=float(s.get("COUNT_TIMER_ONGOING", "2")),
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
    )


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
