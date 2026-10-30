"""Unit + offscreen smoke for skip/overwrite, numbering, and raised crawl limit."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from ytscore import downloader as dl
from ytscore.crawl import CRAWL_LIMIT_MAX, clamp_crawl_limit
from ytscore.settings import Settings, load_settings, save_settings


class DownloadPrefsSettingsTests(unittest.TestCase):
    def test_skip_overwrite_number_roundtrip(self) -> None:
        settings = Settings(
            theme="SuiteDark",
            skip_existing=True,
            overwrite=False,
            number_files=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            save_settings(settings, path)
            loaded = load_settings(path)
            self.assertTrue(loaded.skip_existing)
            self.assertFalse(loaded.overwrite)
            self.assertFalse(loaded.number_files)

    def test_overwrite_wins_on_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            save_settings(
                Settings(skip_existing=True, overwrite=True, number_files=True),
                path,
            )
            loaded = load_settings(path)
            self.assertTrue(loaded.overwrite)
            self.assertFalse(loaded.skip_existing)


class SkipExistingDownloadTests(unittest.TestCase):
    def test_skips_when_file_with_id_exists(self) -> None:
        settings = Settings(
            skip_existing=True,
            overwrite=False,
            number_files=True,
            max_retries=0,
            impersonate="",
            js_runtime="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            existing = os.path.join(tmp, "0001_Prior Title [abc123].mp4")
            with open(existing, "wb") as fh:
                fh.write(b"already")
            with mock.patch.object(dl, "yt_dlp") as fake_mod:
                fake_mod.YoutubeDL = mock.MagicMock(
                    side_effect=AssertionError("should not download")
                )
                result = dl.download_item(
                    "https://www.youtube.com/watch?v=abc123",
                    tmp,
                    settings,
                    media="video",
                    index=1,
                    output_format="mp4",
                )
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.path, existing)

    def test_overwrite_does_not_short_circuit(self) -> None:
        captured: list[dict] = []

        class FakeYDL:
            def __init__(self, opts):
                captured.append(dict(opts))

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=True):
                return {"title": "Fresh", "id": "abc123"}

        settings = Settings(
            skip_existing=True,
            overwrite=True,
            number_files=True,
            max_retries=0,
            impersonate="",
            js_runtime="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            existing = os.path.join(tmp, "0001_Prior Title [abc123].mp4")
            with open(existing, "wb") as fh:
                fh.write(b"old")
            with mock.patch.object(dl, "yt_dlp") as fake_mod, mock.patch.object(
                dl, "apply_auth_opts", side_effect=lambda o, s: o
            ):
                fake_mod.YoutubeDL = FakeYDL
                result = dl.download_item(
                    "https://www.youtube.com/watch?v=abc123",
                    tmp,
                    settings,
                    media="video",
                    index=1,
                    output_format="mp4",
                )
        self.assertTrue(result.ok, result.error)
        self.assertTrue(captured)
        self.assertTrue(captured[0].get("overwrites"))
        self.assertNotIn("download_archive", captured[0])
        self.assertNotIn("nooverwrites", captured[0])

    def test_number_files_off_omits_prefix(self) -> None:
        captured: list[dict] = []

        class FakeYDL:
            def __init__(self, opts):
                captured.append(dict(opts))

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=True):
                return {"title": "NoIndex", "id": "zid"}

        settings = Settings(
            skip_existing=False,
            overwrite=False,
            number_files=False,
            max_retries=0,
            impersonate="",
            js_runtime="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "NoIndex [zid].mp4"), "wb") as fh:
                fh.write(b"data")
            with mock.patch.object(dl, "yt_dlp") as fake_mod, mock.patch.object(
                dl, "apply_auth_opts", side_effect=lambda o, s: o
            ):
                fake_mod.YoutubeDL = FakeYDL
                result = dl.download_item(
                    "https://example.com/v",
                    tmp,
                    settings,
                    media="video",
                    index=7,
                    output_format="mp4",
                )
        self.assertTrue(result.ok, result.error)
        outtmpl = captured[0]["outtmpl"]
        self.assertNotIn("0007_", outtmpl)
        self.assertIn("%(title).180B [%(id)s].%(ext)s", outtmpl)

    def test_skip_sets_archive_and_nooverwrites(self) -> None:
        captured: list[dict] = []

        class FakeYDL:
            def __init__(self, opts):
                captured.append(dict(opts))

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=True):
                return {"title": "New", "id": "newid"}

        settings = Settings(
            skip_existing=True,
            overwrite=False,
            number_files=True,
            max_retries=0,
            impersonate="",
            js_runtime="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "0001_New [newid].mp4"), "wb") as fh:
                fh.write(b"x")
            with mock.patch.object(dl, "yt_dlp") as fake_mod, mock.patch.object(
                dl, "apply_auth_opts", side_effect=lambda o, s: o
            ):
                fake_mod.YoutubeDL = FakeYDL
                # URL with unknown id shape so preflight path skip does not fire.
                result = dl.download_item(
                    "https://example.com/watch?x=newid",
                    tmp,
                    settings,
                    media="video",
                    index=1,
                    output_format="mp4",
                )
        self.assertTrue(result.ok, result.error)
        self.assertTrue(captured[0].get("nooverwrites"))
        self.assertIn("download_archive", captured[0])
        self.assertTrue(
            captured[0]["download_archive"].endswith(dl.DOWNLOAD_ARCHIVE_NAME)
        )


class CrawlLimitUiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def test_download_page_limit_and_file_opts(self) -> None:
        from ytsgui.main_window import SuiteWindow

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            queue_path = os.path.join(tmp, "queue_state.json")
            save_settings(
                Settings(
                    theme="SuiteDark",
                    skip_existing=True,
                    overwrite=False,
                    number_files=True,
                ),
                path,
            )
            with mock.patch(
                "ytsgui.main_window.default_queue_state_path",
                return_value=queue_path,
            ):
                win = SuiteWindow(settings=load_settings(path), config_path=path)
            try:
                win.show()
                self.assertEqual(win.crawl_limit_spin.minimum(), 0)
                self.assertEqual(win.crawl_limit_spin.maximum(), CRAWL_LIMIT_MAX)
                win.crawl_limit_spin.setValue(0)
                self.assertEqual(win._crawl_limit(), 0)
                self.assertEqual(win._crawl_limit_label(), "unlimited")
                win.crawl_limit_spin.setValue(5000)
                self.assertEqual(win._crawl_limit(), 5000)
                self.assertEqual(clamp_crawl_limit(12000), CRAWL_LIMIT_MAX)

                self.assertTrue(win.skip_existing_cb.isChecked())
                self.assertFalse(win.overwrite_cb.isChecked())
                self.assertTrue(win.number_files_cb.isChecked())

                win.overwrite_cb.setChecked(True)
                self.assertTrue(win.settings.overwrite)
                self.assertFalse(win.settings.skip_existing)
                self.assertFalse(win.skip_existing_cb.isChecked())

                win.number_files_cb.setChecked(False)
                self.assertFalse(win.settings.number_files)

                # Persist via Settings form.
                win.settings_overwrite.setChecked(False)
                win.settings_skip_existing.setChecked(True)
                win.settings_number_files.setChecked(False)
                settings = win._settings_from_form()
                save_settings(settings, path)
                reloaded = load_settings(path)
                self.assertTrue(reloaded.skip_existing)
                self.assertFalse(reloaded.overwrite)
                self.assertFalse(reloaded.number_files)
            finally:
                win.close()


if __name__ == "__main__":
    unittest.main()
