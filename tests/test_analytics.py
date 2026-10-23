"""Unit tests for local session analytics and status-bar Suite smoke."""

from __future__ import annotations

import os
import tempfile
import time
import unittest

from ytscore.analytics import SessionAnalytics, format_duration
from ytscore.queue import JobState, QueueJob
from ytscore.settings import Settings, load_settings, save_settings


class FormatDurationTests(unittest.TestCase):
    def test_seconds_and_minutes(self) -> None:
        self.assertEqual(format_duration(12.4), "12.4s")
        self.assertEqual(format_duration(0), "0.0s")
        self.assertTrue(format_duration(65.0).startswith("1m"))


class SessionAnalyticsTests(unittest.TestCase):
    def test_success_error_and_timing(self) -> None:
        stats = SessionAnalytics()
        stats.record_success(10.0)
        stats.record_success(20.0)
        stats.record_failure(5.0)
        self.assertEqual(stats.success_count, 2)
        self.assertEqual(stats.error_count, 1)
        self.assertEqual(stats.last_duration_s, 5.0)
        self.assertAlmostEqual(stats.average_duration_s or 0.0, 35.0 / 3.0)
        text = stats.format_status()
        self.assertIn("OK:2", text)
        self.assertIn("Err:1", text)
        self.assertIn("Last:", text)
        self.assertIn("Avg:", text)

    def test_missing_duration_still_counts(self) -> None:
        stats = SessionAnalytics()
        stats.record_success(None)
        stats.record_failure()
        self.assertEqual(stats.success_count, 1)
        self.assertEqual(stats.error_count, 1)
        self.assertIsNone(stats.last_duration_s)
        self.assertIsNone(stats.average_duration_s)
        self.assertEqual(stats.format_status(), "OK:1  Err:1")

    def test_reset(self) -> None:
        stats = SessionAnalytics()
        stats.record_success(1.0)
        stats.reset()
        self.assertEqual(stats.success_count, 0)
        self.assertEqual(stats.error_count, 0)
        self.assertIsNone(stats.last_duration_s)


class ShowStatusAnalyticsSettingsTests(unittest.TestCase):
    def test_roundtrip_show_status_analytics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            save_settings(
                Settings(theme="SuiteDark", show_status_analytics=False),
                path,
            )
            loaded = load_settings(path)
            self.assertFalse(loaded.show_status_analytics)
            with open(path, encoding="utf-8") as fh:
                body = fh.read().lower()
            self.assertIn("show_status_analytics", body)
            self.assertIn("false", body)

            save_settings(
                Settings(theme="SuiteDark", show_status_analytics=True),
                path,
            )
            self.assertTrue(load_settings(path).show_status_analytics)

    def test_default_when_key_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("[SETTINGS]\nTHEME = SuiteDark\n")
            loaded = load_settings(path)
            self.assertTrue(loaded.show_status_analytics)


class AnalyticsSuiteSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def test_status_label_and_job_tracking(self) -> None:
        from ytsgui.main_window import SuiteWindow

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            save_settings(
                Settings(
                    theme="SuiteDark",
                    cookies_from_browser="brave:Default",
                    show_status_analytics=True,
                ),
                path,
            )
            win = SuiteWindow(settings=load_settings(path), config_path=path)
            try:
                win.show()
                self.assertTrue(hasattr(win, "analytics_label"))
                self.assertFalse(win.analytics_label.isHidden())
                self.assertIn("OK:0", win.analytics_label.text())

                job = QueueJob(
                    id="job-analytics-1",
                    url="https://example.com/video",
                    title="demo",
                    state=JobState.RUNNING,
                    message="Downloading…",
                )
                win._track_job_analytics(job)
                self.assertIn(job.id, win._analytics_started)

                # Simulate elapsed work.
                win._analytics_started[job.id] = time.monotonic() - 2.5
                job.state = JobState.DONE
                job.message = "Done"
                win._track_job_analytics(job)
                self.assertEqual(win.session_analytics.success_count, 1)
                self.assertIn("OK:1", win.analytics_label.text())
                self.assertIn("Last:", win.analytics_label.text())

                # Idempotent: second DONE emit does not double-count.
                win._track_job_analytics(job)
                self.assertEqual(win.session_analytics.success_count, 1)

                # Retry clears counting so a later finish can record again.
                job.state = JobState.QUEUED
                job.message = ""
                win._track_job_analytics(job)
                job.state = JobState.RUNNING
                job.message = "Downloading…"
                win._track_job_analytics(job)
                job.state = JobState.FAILED
                job.message = "boom"
                win._track_job_analytics(job)
                self.assertEqual(win.session_analytics.error_count, 1)
                self.assertIn("Err:1", win.analytics_label.text())

                # Toggle off via settings apply.
                win.settings_show_analytics.setChecked(False)
                settings = win._settings_from_form()
                self.assertFalse(settings.show_status_analytics)
                save_settings(settings, path)
                win._apply_settings_runtime(settings)
                self.assertTrue(win.analytics_label.isHidden())
                reloaded = load_settings(path)
                self.assertFalse(reloaded.show_status_analytics)
            finally:
                win.close()


if __name__ == "__main__":
    unittest.main()
