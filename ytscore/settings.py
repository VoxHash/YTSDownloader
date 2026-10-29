"""Load and expose application settings from config.ini."""

from __future__ import annotations

import configparser
import glob
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Optional, Tuple

from ytscore.formats import DEFAULT_VIDEO_FORMAT, normalize_video_format

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
    video_format_pref: str = DEFAULT_VIDEO_FORMAT
    # Exponential backoff between download retries (and harder on HTTP 429).
    backoff_base: float = 2.0
    backoff_factor: float = 2.0
    backoff_max: float = 90.0
    # Local session counters in the Suite status bar (no network telemetry).
    show_status_analytics: bool = True
    # Desktop coexistence: lower CPU nice and/or idle I/O when the queue starts.
    # nice 0 = leave CPU priority alone; idle_io defaults on for Linux disk politeness.
    process_nice: int = 0
    process_idle_io: bool = True
    # Optional yt-dlp TLS / HTTP impersonation client (e.g. chrome). Empty = off.
    # Requires curl_cffi (see requirements.txt). Helps hosts that block plain clients.
    impersonate: str = "chrome"

    def cookies_tuple(self) -> Optional[Tuple[str, ...]]:
        parts = [p.strip() for p in self.cookies_from_browser.split(":") if p.strip()]
        return tuple(parts) if parts else None


def _as_bool(value: str, default: bool = True) -> bool:
    text = (value or "").strip().lower()
    if not text:
        return default
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    return default


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
        video_format_pref=normalize_video_format(
            s.get("VIDEO_FORMAT", DEFAULT_VIDEO_FORMAT)
        ),
        backoff_base=max(0.0, float(s.get("BACKOFF_BASE", "2"))),
        backoff_factor=max(1.0, float(s.get("BACKOFF_FACTOR", "2"))),
        backoff_max=max(0.0, float(s.get("BACKOFF_MAX", "90"))),
        show_status_analytics=_as_bool(s.get("SHOW_STATUS_ANALYTICS", "true"), True),
        process_nice=max(0, min(19, int(s.get("PROCESS_NICE", "0")))),
        process_idle_io=_as_bool(s.get("PROCESS_IDLE_IO", "true"), True),
        impersonate=s.get("IMPERSONATE", "chrome").strip(),
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
    s["VIDEO_FORMAT"] = normalize_video_format(settings.video_format_pref)
    s["DEFAULT_OUTPUT"] = (settings.default_output or "").strip()
    s["SHOW_STATUS_ANALYTICS"] = (
        "true" if bool(settings.show_status_analytics) else "false"
    )
    s["PROCESS_NICE"] = str(max(0, min(19, int(settings.process_nice))))
    s["PROCESS_IDLE_IO"] = "true" if bool(settings.process_idle_io) else "false"
    s["IMPERSONATE"] = (settings.impersonate or "").strip()

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


def _impersonate_target(value: str):
    """Parse IMPERSONATE into a yt-dlp ImpersonateTarget, or None."""
    text = (value or "").strip()
    if not text:
        return None
    try:
        from yt_dlp.networking.impersonate import ImpersonateTarget

        return ImpersonateTarget.from_str(text.lower())
    except Exception:
        return None


def _fnm_runtime_candidates(runtime: str) -> list:
    """Locate fnm-managed binaries when PATH lacks them (common for GUI Suite launches)."""
    home = os.path.expanduser("~")
    versions_root = os.path.join(home, ".local", "share", "fnm", "node-versions")
    if not os.path.isdir(versions_root):
        return []
    # Prefer highest version directory (names like v24.22.1).
    pattern = os.path.join(versions_root, "*", "installation", "bin", runtime)
    paths = sorted(glob.glob(pattern), reverse=True)
    return [p for p in paths if os.path.isfile(p) and os.access(p, os.X_OK)]


def resolve_js_runtime_path(runtime: str, explicit_path: str = "") -> Optional[str]:
    """
    Resolve an executable path for *runtime* (node / deno / bun / …).

    Order: explicit path → PATH (shutil.which) → fnm node-versions (node only).
    """
    name = (runtime or "").strip()
    if not name:
        return None
    explicit = (explicit_path or "").strip()
    if explicit:
        expanded = os.path.expanduser(explicit)
        if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
            return expanded
        logging.warning("JS_RUNTIME_PATH not executable: %s", explicit)
    found = shutil.which(name)
    if found:
        return found
    if name == "node":
        for candidate in _fnm_runtime_candidates("node"):
            return candidate
    return None


def apply_auth_opts(ydl_opts: dict, settings: Settings) -> dict:
    ydl_opts = dict(ydl_opts)
    ydl_opts["no_color"] = True
    # Allow fetching the external JS challenge solver used by modern extractors.
    ydl_opts.setdefault("remote_components", {"ejs:github"})
    if settings.js_runtime:
        runtime = settings.js_runtime.strip()
        path = resolve_js_runtime_path(runtime, settings.js_runtime_path)
        if path:
            ydl_opts["js_runtimes"] = {runtime: {"path": path}}
        else:
            # Still declare the runtime so yt-dlp can search; warn for Suite operators.
            ydl_opts["js_runtimes"] = {runtime: {}}
            logging.warning(
                "JS runtime %r not found on PATH (or JS_RUNTIME_PATH); "
                "YouTube may only expose storyboard images until Node/Deno is installed",
                runtime,
            )
    cookies = settings.cookies_tuple()
    if cookies:
        ydl_opts["cookiesfrombrowser"] = cookies
    elif settings.cookies_file:
        ydl_opts["cookiefile"] = settings.cookies_file
    # Prefer an explicit impersonate target when curl_cffi (or peers) can serve it.
    # Extractors may also request impersonation; setting a default helps plain clients.
    if "impersonate" not in ydl_opts:
        target = _impersonate_target(settings.impersonate)
        if target is not None:
            ydl_opts["impersonate"] = target
    return ydl_opts
