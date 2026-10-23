"""Theme loading helpers."""

from __future__ import annotations

import os


def load_stylesheet(theme: str) -> str:
    candidates = [
        os.path.join("themes", theme, "style.qss"),
        os.path.join("themes", "SuiteDark", "style.qss"),
        os.path.join("themes", "DarkFreeze", "style.qss"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
    return ""
