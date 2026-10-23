"""Unit tests for failure classification and one-click retry."""

from __future__ import annotations

import os
import tempfile
import unittest

from ytscore.queue import DownloadQueue, JobState, QueueJob
from ytscore.settings import Settings
from ytscore.triage import (
    FailureCategory,
    category_label,
    classify_failure,
    failure_detail_text,
)


class ClassifyFailureTests(unittest.TestCase):
    def test_rate_limit(self) -> None:
        self.assertEqual(
            classify_failure("HTTP Error 429: Too Many Requests"),
            FailureCategory.RATE_LIMIT,
        )

    def test_auth(self) -> None:
        self.assertEqual(
            classify_failure("Sign in to confirm you're not a bot"),
            FailureCategory.AUTH,
        )
        self.assertEqual(
            classify_failure("ERROR: Private video; cookies required"),
            FailureCategory.AUTH,
        )

    def test_unavailable(self) -> None:
        self.assertEqual(
            classify_failure("ERROR: Video unavailable"),
            FailureCategory.UNAVAILABLE,
        )
        self.assertEqual(
            classify_failure("HTTP Error 404: Not Found"),
            FailureCategory.UNAVAILABLE,
        )

    def test_format(self) -> None:
        self.assertEqual(
            classify_failure("Postprocessing: ffmpeg not found"),
            FailureCategory.FORMAT,
        )

    def test_network_temporary(self) -> None:
        self.assertEqual(
            classify_failure("Connection reset by peer"),
            FailureCategory.NETWORK,
        )

    def test_unknown_and_empty(self) -> None:
        self.assertEqual(classify_failure(""), FailureCategory.UNKNOWN)
        self.assertEqual(classify_failure(None), FailureCategory.UNKNOWN)
        self.assertEqual(classify_failure("something odd happened"), FailureCategory.UNKNOWN)

    def test_detail_text_includes_category(self) -> None:
        text = failure_detail_text(
            title="Demo",
            url="https://example.com/v",
            state="failed",
            error="HTTP Error 429: Too Many Requests",
        )
        self.assertIn("Rate limit", text)
        self.assertIn("https://example.com/v", text)
        self.assertIn(category_label(FailureCategory.RATE_LIMIT), text)


class RetryQueueTests(unittest.TestCase):
    def test_retry_preserves_export_options(self) -> None:
        q = DownloadQueue(settings=Settings(), output_dir="/tmp/yts-triage-out")
        job = q.add(
            "https://example.com/a",
            media="audio",
            title="Keep me",
            watermark_path="",
            output_format="m4a",
        )
        job.state = JobState.FAILED
        job.progress = 42.0
        job.error = "HTTP Error 429: Too Many Requests"
        job.message = job.error
        job.path = "/tmp/partial.m4a"

        n = q.retry_jobs([job.id])
        self.assertEqual(n, 1)
        restored = q.get(job.id)
        assert restored is not None
        self.assertEqual(restored.state, JobState.QUEUED)
        self.assertEqual(restored.progress, 0.0)
        self.assertIsNone(restored.error)
        self.assertIsNone(restored.path)
        self.assertEqual(restored.message, "Queued for retry")
        self.assertEqual(restored.url, "https://example.com/a")
        self.assertEqual(restored.title, "Keep me")
        self.assertEqual(restored.media, "audio")
        self.assertEqual(restored.output_format, "m4a")
        self.assertEqual(restored.watermark_path, "")

    def test_retry_failed_skips_cancelled(self) -> None:
        q = DownloadQueue(settings=Settings(), output_dir="/tmp/yts-triage-out")
        a = q.add("https://example.com/1", media="video")
        b = q.add("https://example.com/2", media="video")
        a.state = JobState.FAILED
        a.error = "boom"
        b.state = JobState.CANCELLED
        n = q.retry_failed()
        self.assertEqual(n, 1)
        self.assertEqual(q.get(a.id).state, JobState.QUEUED)
        self.assertEqual(q.get(b.id).state, JobState.CANCELLED)

    def test_retry_selected_includes_cancelled(self) -> None:
        q = DownloadQueue(settings=Settings(), output_dir="/tmp/yts-triage-out")
        a = q.add("https://example.com/1", media="video")
        b = q.add("https://example.com/2", media="video")
        c = q.add("https://example.com/3", media="video")
        a.state = JobState.FAILED
        b.state = JobState.CANCELLED
        c.state = JobState.DONE
        n = q.retry_jobs([a.id, b.id, c.id])
        self.assertEqual(n, 2)
        self.assertEqual(q.get(a.id).state, JobState.QUEUED)
        self.assertEqual(q.get(b.id).state, JobState.QUEUED)
        self.assertEqual(q.get(c.id).state, JobState.DONE)

    def test_retry_ignores_running_and_queued(self) -> None:
        q = DownloadQueue(settings=Settings(), output_dir="/tmp/yts-triage-out")
        a = q.add("https://example.com/1", media="video")
        b = q.add("https://example.com/2", media="video")
        a.state = JobState.RUNNING
        b.state = JobState.QUEUED
        self.assertEqual(q.retry_jobs([a.id, b.id]), 0)


class TriageUiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def test_triage_panel_and_retry_actions(self) -> None:
        from ytsgui.main_window import SuiteWindow

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            from ytscore.settings import save_settings

            save_settings(Settings(theme="SuiteDark", cookies_from_browser="brave:Default"), path)
            win = SuiteWindow(settings=Settings(theme="SuiteDark"), config_path=path)
            try:
                self.assertTrue(hasattr(win, "triage_detail"))
                self.assertTrue(hasattr(win, "triage_category"))
                q = win._ensure_queue()
                job = q.add(
                    "https://example.com/smoke-fail",
                    media="video",
                    watermark_path="/tmp/wm.png",
                    output_format="mp4",
                )
                job.state = JobState.FAILED
                job.error = "Sign in to confirm you're not a bot"
                job.message = job.error
                job.progress = 18.0
                win._upsert_job_row(job)
                win.queue_table.selectRow(win._job_rows[job.id])
                win._refresh_failure_triage()
                self.assertIn("Auth", win.triage_category.text())
                self.assertIn("example.com/smoke-fail", win.triage_detail.toPlainText())

                n = q.retry_jobs([job.id])
                self.assertEqual(n, 1)
                refreshed = q.get(job.id)
                assert refreshed is not None
                self.assertEqual(refreshed.state, JobState.QUEUED)
                self.assertEqual(refreshed.watermark_path, "/tmp/wm.png")
                self.assertEqual(refreshed.output_format, "mp4")
                win._upsert_job_row(refreshed)
                win._refresh_failure_triage()
                # After retry the selected job is queued — category shows state hint.
                self.assertIn("queued", win.triage_category.text().lower())
            finally:
                win.close()


if __name__ == "__main__":
    unittest.main()
