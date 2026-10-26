"""Unit tests for config.ini write/read round-trip and Settings UI smoke."""

from __future__ import annotations

import os
import tempfile
import unittest

from ytscore.settings import Settings, load_settings, save_settings


class SettingsRoundTripTests(unittest.TestCase):
    def test_save_load_roundtrip(self) -> None:
        settings = Settings(
            theme="SuiteDark",
            pace_seconds=3.25,
            cookies_from_browser="brave:Default",
            cookies_file="",
            js_runtime="node",
            js_runtime_path="",
            max_workers=4,
            max_retries=5,
            default_output="/tmp/yts-out",
            audio_format="mp3",
            video_format_pref="best",
            backoff_base=1.5,
            backoff_factor=3.0,
            backoff_max=60.0,
            show_status_analytics=False,
            impersonate="chrome120",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            save_settings(settings, path)
            loaded = load_settings(path)
            self.assertEqual(loaded.theme, "SuiteDark")
            self.assertEqual(loaded.pace_seconds, 3.25)
            self.assertEqual(loaded.cookies_from_browser, "brave:Default")
            self.assertEqual(loaded.cookies_file, "")
            self.assertEqual(loaded.js_runtime, "node")
            self.assertEqual(loaded.js_runtime_path, "")
            self.assertEqual(loaded.max_workers, 4)
            self.assertEqual(loaded.max_retries, 5)
            self.assertEqual(loaded.default_output, "/tmp/yts-out")
            self.assertEqual(loaded.audio_format, "mp3")
            self.assertEqual(loaded.video_format_pref, "best")
            self.assertEqual(loaded.backoff_base, 1.5)
            self.assertEqual(loaded.backoff_factor, 3.0)
            self.assertEqual(loaded.backoff_max, 60.0)
            self.assertFalse(loaded.show_status_analytics)
            self.assertEqual(loaded.impersonate, "chrome120")

    def test_save_load_empty_impersonate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            save_settings(Settings(theme="SuiteDark", impersonate=""), path)
            loaded = load_settings(path)
            self.assertEqual(loaded.impersonate, "")

    def test_atomic_replace_preserves_brave_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("[SETTINGS]\nTHEME = SuiteDark\nCOOKIES_FROM_BROWSER = firefox\n")
            save_settings(
                Settings(theme="SuiteDark", cookies_from_browser="brave:Default"),
                path,
            )
            loaded = load_settings(path)
            self.assertEqual(loaded.cookies_from_browser, "brave:Default")
            self.assertTrue(os.path.isfile(path))
            self.assertFalse(os.path.exists(path + ".tmp"))


class SettingsUiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def test_form_save_reload_roundtrip(self) -> None:
        from ytsgui.main_window import SuiteWindow

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            initial = Settings(
                theme="SuiteDark",
                pace_seconds=2.5,
                cookies_from_browser="brave:Default",
                js_runtime="node",
                max_workers=2,
                max_retries=3,
                backoff_base=2.0,
                backoff_factor=2.0,
                backoff_max=90.0,
                audio_format="m4a",
                video_format_pref="bestvideo+bestaudio/best",
                impersonate="chrome",
            )
            save_settings(initial, path)
            win = SuiteWindow(settings=load_settings(path), config_path=path)
            try:
                win.settings_pace.setValue(4.0)
                win.settings_max_workers.setValue(3)
                win.settings_cookies_browser.setText("brave:Default")
                win.settings_backoff_max.setValue(120.0)
                win.settings_default_output.setText("/tmp/yts-suite-out")
                win.settings_impersonate.setEditText("firefox")
                # Exercise save path without modal dialogs.
                settings = win._settings_from_form()
                save_settings(settings, path)
                win._apply_settings_runtime(settings)
                win._fill_settings_form(settings)

                reloaded = load_settings(path)
                self.assertEqual(reloaded.pace_seconds, 4.0)
                self.assertEqual(reloaded.max_workers, 3)
                self.assertEqual(reloaded.cookies_from_browser, "brave:Default")
                self.assertEqual(reloaded.backoff_max, 120.0)
                self.assertEqual(reloaded.default_output, "/tmp/yts-suite-out")
                self.assertEqual(reloaded.impersonate, "firefox")
                self.assertEqual(win.settings.max_workers, 3)
                self.assertEqual(win.settings.pace_seconds, 4.0)
                self.assertEqual(win.settings.impersonate, "firefox")
            finally:
                win.close()

    def test_impersonate_form_empty_disables(self) -> None:
        from ytsgui.main_window import SuiteWindow

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            save_settings(
                Settings(theme="SuiteDark", impersonate="chrome"),
                path,
            )
            win = SuiteWindow(settings=load_settings(path), config_path=path)
            try:
                self.assertEqual(win.settings_impersonate.currentText().strip(), "chrome")
                win.settings_impersonate.setEditText("")
                settings = win._settings_from_form()
                self.assertEqual(settings.impersonate, "")
                save_settings(settings, path)
                win._apply_settings_runtime(settings)
                self.assertEqual(win.settings.impersonate, "")
                self.assertEqual(load_settings(path).impersonate, "")
            finally:
                win.close()


if __name__ == "__main__":
    unittest.main()
