"""Resolve YTSDownloader application icon paths."""

from __future__ import annotations

import os
import sys
from typing import List, Optional


def project_root() -> str:
    """Repo root (parent of ``ytscore/``), or PyInstaller bundle root when frozen."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.abspath(sys._MEIPASS)  # type: ignore[attr-defined]
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def icon_candidates() -> List[str]:
    """Preferred icon files (PNG first for Qt, then SVG)."""
    root = project_root()
    icons = os.path.join(root, "assets", "icons")
    cwd_icons = os.path.join(os.getcwd(), "assets", "icons")
    bases = [icons]
    if cwd_icons != icons:
        bases.append(cwd_icons)
    paths: List[str] = []
    for base in bases:
        paths.extend(
            [
                os.path.join(base, "256x256", "ytsdownloader.png"),
                os.path.join(base, "ytsdownloader.png"),
                os.path.join(base, "128x128", "ytsdownloader.png"),
                os.path.join(base, "scalable", "ytsdownloader.svg"),
                os.path.join(base, "ytsdownloader.svg"),
            ]
        )
    return paths

def resolve_app_icon_path() -> Optional[str]:
    """Return the first existing app icon path, or ``None``."""
    for path in icon_candidates():
        if os.path.isfile(path):
            return path
    return None
