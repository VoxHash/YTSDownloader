"""Application entry helpers."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from ytscore.settings import load_settings
from ytsgui.main_window import SuiteWindow


def run_suite(argv=None) -> int:
    argv = argv if argv is not None else sys.argv
    app = QApplication(argv)
    settings = load_settings()
    window = SuiteWindow(settings)
    window.show()
    return app.exec()
