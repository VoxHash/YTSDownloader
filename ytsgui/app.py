"""Application entry helpers."""

from __future__ import annotations

import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from ytscore.icons import resolve_app_icon_path
from ytscore.settings import load_settings
from ytsgui.main_window import SuiteWindow


def apply_app_icon(app: QApplication) -> None:
    """Set the process / window icon from assets/icons when present."""
    path = resolve_app_icon_path()
    if not path:
        return
    icon = QIcon(path)
    app.setWindowIcon(icon)


def run_suite(argv=None) -> int:
    argv = argv if argv is not None else sys.argv
    app = QApplication(argv)
    apply_app_icon(app)
    settings = load_settings()
    window = SuiteWindow(settings)
    path = resolve_app_icon_path()
    if path:
        window.setWindowIcon(QIcon(path))
    window.show()
    return app.exec()
