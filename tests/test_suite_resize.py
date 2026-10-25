"""Offscreen smoke: SuiteWindow can shrink and grow freely."""

from __future__ import annotations

import os
import tempfile
import unittest

from ytscore.settings import Settings


class SuiteResizeSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def _make_window(self):
        from ytsgui.main_window import SuiteWindow

        tmp = tempfile.NamedTemporaryFile(suffix=".ini", delete=False)
        tmp.close()
        self.addCleanup(lambda: os.path.exists(tmp.name) and os.unlink(tmp.name))
        win = SuiteWindow(
            settings=Settings(theme="SuiteDark"),
            config_path=tmp.name,
        )
        self.addCleanup(win.close)
        return win

    def test_not_fixed_size(self) -> None:
        win = self._make_window()
        self.assertLess(win.minimumWidth(), win.maximumWidth())
        self.assertLess(win.minimumHeight(), win.maximumHeight())
        self.assertEqual(win.minimumWidth(), 640)
        self.assertEqual(win.minimumHeight(), 480)
        self.assertGreaterEqual(win.maximumWidth(), 10000)
        self.assertGreaterEqual(win.maximumHeight(), 10000)

    def test_minimum_size_hint_allows_small_screens(self) -> None:
        win = self._make_window()
        # Force Metadata Bridge status (historically inflated stack min width).
        win._poll_spotify_session()
        hint = win.minimumSizeHint()
        self.assertLessEqual(
            hint.width(),
            900,
            f"minimumSizeHint width too large for free resize: {hint.width()}",
        )
        self.assertLessEqual(
            hint.height(),
            700,
            f"minimumSizeHint height too large for free resize: {hint.height()}",
        )

    def test_resize_shrink_and_grow(self) -> None:
        win = self._make_window()
        win._poll_spotify_session()
        sizes = [
            (1120, 720),
            (960, 600),
            (800, 560),
            (720, 520),
            (640, 480),
            (1280, 800),
            (1600, 900),
            (640, 480),
        ]
        for width, height in sizes:
            win.resize(width, height)
            actual = win.size()
            self.assertEqual(actual.width(), width, f"width after resize({width},{height})")
            self.assertEqual(actual.height(), height, f"height after resize({width},{height})")
            # Visit each page so layouts reflow under the new size.
            for index in range(win.stack.count()):
                win._set_page(index)
                self.assertEqual(win.stack.currentIndex(), index)

    def test_compact_ui_text_caps_width_drivers(self) -> None:
        from ytsgui.main_window import SuiteWindow

        long_msg = "x" * 500
        compact = SuiteWindow._compact_ui_text(long_msg, 160)
        self.assertLessEqual(len(compact), 160)
        self.assertTrue(compact.endswith("…"))

    def test_sidebar_fixed_does_not_equal_window_fixed(self) -> None:
        win = self._make_window()
        self.assertEqual(win.sidebar.minimumWidth(), win.sidebar.maximumWidth())
        self.assertEqual(win.sidebar.width(), 220)
        self.assertNotEqual(win.minimumWidth(), win.maximumWidth())


if __name__ == "__main__":
    unittest.main()
