"""Unit + offscreen smoke for large-queue filter/page/throttle helpers."""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from unittest import mock

from ytscore.persist import save_queue_state, serialize_queue_snapshot
from ytscore.queue import DownloadQueue, JobState, QueueJob
from ytscore.queue_view import (
    QUEUE_TABLE_PAGE_SIZE,
    UI_FLUSH_INTERVAL_MS,
    filter_jobs,
    job_matches_filters,
    paginate_jobs,
    persist_debounce_ms,
    persist_json_indent,
)
from ytscore.settings import Settings


def _job(
    i: int,
    *,
    state: JobState = JobState.QUEUED,
    title: str = "",
    message: str = "",
) -> QueueJob:
    return QueueJob(
        id=f"id-{i}",
        url=f"https://example.com/{i}",
        title=title or f"Title {i}",
        state=state,
        progress=float(i % 100),
        message=message,
        index=i,
    )


class QueueViewHelperTests(unittest.TestCase):
    def test_job_matches_state_and_search(self) -> None:
        failed = _job(1, state=JobState.FAILED, message="temporary (network)")
        queued = _job(2, state=JobState.QUEUED, title="Alpha Clip")
        self.assertTrue(job_matches_filters(failed, "failed", ""))
        self.assertFalse(job_matches_filters(queued, "failed", ""))
        self.assertTrue(job_matches_filters(queued, "", "alpha"))
        self.assertTrue(job_matches_filters(failed, "failed", "network"))
        self.assertFalse(job_matches_filters(failed, "failed", "missing"))

    def test_filter_and_paginate_scale(self) -> None:
        jobs = [_job(i, state=JobState.QUEUED) for i in range(1, 1201)]
        jobs[10].state = JobState.FAILED
        jobs[11].state = JobState.FAILED
        jobs[12].state = JobState.FAILED
        matched = filter_jobs(jobs, "failed", "")
        self.assertEqual(len(matched), 3)
        page, page_i, pages, total = paginate_jobs(matched, 0, page_size=2)
        self.assertEqual([j.id for j in page], ["id-11", "id-12"])
        self.assertEqual(page_i, 0)
        self.assertEqual(pages, 2)
        self.assertEqual(total, 3)

        all_page, page_i, pages, total = paginate_jobs(jobs, 0)
        self.assertEqual(len(all_page), QUEUE_TABLE_PAGE_SIZE)
        self.assertEqual(page_i, 0)
        self.assertEqual(total, 1200)
        self.assertGreater(pages, 1)

    def test_persist_pacing_scales_with_n(self) -> None:
        self.assertLess(persist_debounce_ms(10), persist_debounce_ms(5000))
        self.assertEqual(persist_json_indent(10), 2)
        self.assertIsNone(persist_json_indent(5000))

    def test_compact_save_for_large_snapshot(self) -> None:
        jobs = [_job(i) for i in range(1, 501)]
        snap = serialize_queue_snapshot(
            jobs=jobs, output_dir="/tmp/out", watermark_path="", output_format="mp4"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "queue_state.json")
            save_queue_state(path, snap, indent=None)
            with open(path, encoding="utf-8") as fh:
                raw = fh.read()
            # Compact JSON has no pretty indentation after the opening brace line.
            self.assertNotIn("\n  ", raw)

    def test_progress_stats_and_emit_throttle(self) -> None:
        q = DownloadQueue(settings=Settings(), output_dir="/tmp/yts-qv")
        emits: list[str] = []
        q.add_listener(lambda job: emits.append(job.id))
        a = q.add("https://example.com/a")
        b = q.add("https://example.com/b")
        a.state = JobState.DONE
        a.progress = 100.0
        b.state = JobState.FAILED
        b.progress = 10.0
        total, done, failed, avg = q.progress_stats()
        self.assertEqual(total, 2)
        self.assertEqual(done, 1)
        self.assertEqual(failed, 1)
        self.assertGreater(avg, 0.0)
        self.assertEqual(q.job_count(), 2)

        # Simulate progress hook throttling path used by _run_job.
        from ytscore.queue_view import PROGRESS_EMIT_MIN_INTERVAL_S

        job = q.get(a.id)
        assert job is not None
        before = len(emits)
        last = [0.0]

        def emit_throttled() -> None:
            now = time.monotonic()
            if now - last[0] < PROGRESS_EMIT_MIN_INTERVAL_S:
                return
            last[0] = now
            q._emit(job)

        emit_throttled()
        emit_throttled()
        self.assertEqual(len(emits), before + 1)


class LargeQueueUiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def test_table_caps_rows_and_flush_updates_in_place(self) -> None:
        from ytsgui.main_window import SuiteWindow
        from ytscore.settings import save_settings

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            save_settings(Settings(theme="SuiteDark"), path)
            win = SuiteWindow(settings=Settings(theme="SuiteDark"), config_path=path)
            try:
                win._persist_enabled = False
                win._queue_state_path = os.path.join(tmp, "queue_state.json")
                if win.queue:
                    win.queue.clear_all()
                q = win._ensure_queue()
                q.clear_all()

                # Seed a large restored-style queue without per-row Qt inserts.
                bulk = [
                    QueueJob(
                        id=f"bulk-{i}",
                        url=f"https://example.com/v/{i}",
                        title=f"Item {i}",
                        state=JobState.QUEUED if i % 200 else JobState.FAILED,
                        progress=0.0,
                        message="boom" if i % 200 == 0 else "",
                        error="boom" if i % 200 == 0 else None,
                        index=i,
                    )
                    for i in range(1, 3001)
                ]
                q.restore_jobs(bulk)
                win._queue_page = 0
                win.queue_state_filter.setCurrentIndex(0)  # All
                win._refresh_queue_view()
                self.assertEqual(win.queue_table.rowCount(), QUEUE_TABLE_PAGE_SIZE)
                self.assertEqual(q.job_count(), 3000)

                # Failed filter should only render the matching subset (≤ page size).
                failed_idx = win.queue_state_filter.findData("failed")
                self.assertGreaterEqual(failed_idx, 0)
                win.queue_state_filter.setCurrentIndex(failed_idx)
                win._filter_debounce_timer.stop()
                win._refresh_queue_view()
                failed_n = sum(1 for j in q.jobs() if j.state == JobState.FAILED)
                self.assertEqual(win.queue_table.rowCount(), min(failed_n, QUEUE_TABLE_PAGE_SIZE))
                self.assertLess(win.queue_table.rowCount(), 100)

                # Coalesced flush updates progress cells without growing the table.
                sample_id = win._row_jobs[0]
                sample = q.get(sample_id)
                assert sample is not None
                sample.progress = 77.0
                sample.message = "77.0%"
                win._pending_job_updates[sample.id] = sample
                win._flush_pending_job_updates()
                self.assertEqual(win.queue_table.item(0, 4).text(), "77%")
                self.assertEqual(win.queue_table.rowCount(), min(failed_n, QUEUE_TABLE_PAGE_SIZE))

                # Persist debounce helper is consulted for large N.
                self.assertGreaterEqual(persist_debounce_ms(q.job_count()), UI_FLUSH_INTERVAL_MS)
            finally:
                win.close()

    def test_progress_hook_throttles_emits(self) -> None:
        q = DownloadQueue(
            settings=Settings(max_workers=1, pace_seconds=0.0),
            output_dir="/tmp/yts-qv2",
        )
        emits = []
        q.add_listener(lambda job: emits.append((job.progress, job.message)))

        job = q.add("https://example.com/throttle")
        # Drive the private hook logic via a fake download path.
        with mock.patch("ytscore.queue.download_item") as dl:
            from ytscore.downloader import DownloadResult

            def fake_download(*_a, **kwargs):
                hook = kwargs.get("progress_hook")
                assert hook is not None
                for pct in (10, 20, 30, 40, 50):
                    hook(
                        {
                            "status": "downloading",
                            "total_bytes": 100,
                            "downloaded_bytes": pct,
                            "_percent_str": f"{pct}%",
                        }
                    )
                return DownloadResult(ok=True, path="/tmp/x.mp4", title="x")

            dl.side_effect = fake_download
            q.start()
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                refreshed = q.get(job.id)
                if refreshed and refreshed.state == JobState.DONE:
                    break
                time.sleep(0.02)
            q.stop()

        # Five progress ticks coalesce to one emit when they arrive in one burst.
        progress_emits = [e for e in emits if e[0] < 100.0 and e[0] > 0.0]
        self.assertLessEqual(len(progress_emits), 2)
        self.assertGreaterEqual(len(progress_emits), 1)


if __name__ == "__main__":
    unittest.main()
