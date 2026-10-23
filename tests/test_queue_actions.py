"""Unit + offscreen tests for remove / clear all / force download + folder sidebar."""

from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from unittest import mock

from ytscore.folder_dialog import discover_mount_points, volume_sidebar_paths
from ytscore.queue import DownloadQueue, JobState, QueueJob
from ytscore.settings import Settings


class FolderSidebarTests(unittest.TestCase):
    def test_discover_mount_points_from_proc_text(self) -> None:
        proc = (
            "/dev/sda1 / ext4 rw 0 0\n"
            "/dev/sdb1 /run/media/raider/USB_DRIVE vfat rw 0 0\n"
            "/dev/sdc1 /mnt/data ext4 rw 0 0\n"
            "tmpfs /run/user/1000 tmpfs rw 0 0\n"
        )
        with mock.patch("os.path.isdir", return_value=True), mock.patch(
            "os.listdir", return_value=[]
        ), mock.patch.dict(os.environ, {"USER": "raider"}, clear=False):
            mounts = discover_mount_points(proc_mounts=proc)
        self.assertIn("/run/media/raider", mounts)
        self.assertIn("/run/media/raider/USB_DRIVE", mounts)
        self.assertIn("/mnt/data", mounts)
        self.assertNotIn("/run/user/1000", mounts)

    def test_volume_sidebar_paths_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = os.path.join(tmp, "home")
            downloads = os.path.join(home, "Downloads")
            usb = os.path.join(tmp, "usb")
            os.makedirs(downloads)
            os.makedirs(usb)
            paths = volume_sidebar_paths(
                home=home,
                downloads=downloads,
                proc_mounts="",
                extra=[usb],
            )
            self.assertEqual(paths[0], os.path.abspath(home))
            self.assertEqual(paths[1], os.path.abspath(downloads))
            self.assertIn(os.path.abspath(usb), paths)


class QueueRemoveClearForceTests(unittest.TestCase):
    def test_remove_jobs(self) -> None:
        q = DownloadQueue(settings=Settings(), output_dir="/tmp/yts-q-out")
        a = q.add("https://example.com/a")
        b = q.add("https://example.com/b")
        c = q.add("https://example.com/c")
        n = q.remove_jobs([a.id, c.id])
        self.assertEqual(n, 2)
        remaining = q.jobs()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].id, b.id)

    def test_clear_all(self) -> None:
        q = DownloadQueue(settings=Settings(), output_dir="/tmp/yts-q-out")
        q.add("https://example.com/1")
        q.add("https://example.com/2")
        n = q.clear_all()
        self.assertEqual(n, 2)
        self.assertEqual(q.jobs(), [])

    def test_force_download_bumps_front_and_skips_pace(self) -> None:
        settings = Settings(pace_seconds=30.0, max_workers=1)
        q = DownloadQueue(settings=settings, output_dir="/tmp/yts-q-out")
        first = q.add("https://example.com/first")
        second = q.add("https://example.com/second")
        # Simulate a long pace gate already reserved.
        q._next_start_at = time.monotonic() + 60.0

        started = threading.Event()
        original_wait = q._wait_for_pace_slot

        def tracking_wait(job: QueueJob) -> None:
            started.set()
            original_wait(job)

        q._wait_for_pace_slot = tracking_wait  # type: ignore[method-assign]

        with mock.patch("ytscore.queue.download_item") as dl:
            from ytscore.downloader import DownloadResult

            dl.return_value = DownloadResult(
                ok=True, path="/tmp/out.mp4", title="t", error=None
            )
            self.assertTrue(q.force_download(second.id))
            self.assertEqual(q.jobs()[0].id, second.id)
            self.assertIn(second.id, q._force_ids)
            # Force starts workers even when queue was stopped.
            self.assertTrue(q.is_running)
            # Pace skip should let the job leave the wait quickly.
            self.assertTrue(started.wait(timeout=2.0))
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                job = q.get(second.id)
                if job and job.state == JobState.DONE:
                    break
                time.sleep(0.05)
            job = q.get(second.id)
            assert job is not None
            self.assertEqual(job.state, JobState.DONE)
            # first remains queued (not auto-started by force of second alone
            # beyond whatever start() pending submit — force only submits target).
            self.assertEqual(q.get(first.id).state, JobState.QUEUED)  # type: ignore[union-attr]
            q.stop()

    def test_force_download_retries_failed(self) -> None:
        q = DownloadQueue(settings=Settings(pace_seconds=0.0), output_dir="/tmp/yts-q-out")
        job = q.add(
            "https://example.com/fail",
            media="video",
            watermark_path="/tmp/wm.png",
            output_format="webm",
        )
        job.state = JobState.FAILED
        job.error = "boom"
        job.message = "boom"
        job.progress = 12.0
        with mock.patch("ytscore.queue.download_item") as dl:
            from ytscore.downloader import DownloadResult

            dl.return_value = DownloadResult(
                ok=True, path="/tmp/out.webm", title="ok", error=None
            )
            self.assertTrue(q.force_download(job.id))
            refreshed = q.get(job.id)
            assert refreshed is not None
            self.assertEqual(refreshed.watermark_path, "/tmp/wm.png")
            self.assertEqual(refreshed.output_format, "webm")
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                if refreshed.state == JobState.DONE:
                    break
                time.sleep(0.05)
                refreshed = q.get(job.id)
                assert refreshed is not None
            self.assertEqual(refreshed.state, JobState.DONE)
            q.stop()


class QueueActionsUiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def test_clear_all_and_context_actions_wired(self) -> None:
        from ytsgui.main_window import SuiteWindow
        from ytscore.settings import save_settings
        from ytscore.persist import load_queue_state

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            save_settings(Settings(theme="SuiteDark"), path)
            win = SuiteWindow(settings=Settings(theme="SuiteDark"), config_path=path)
            try:
                # Isolate from the developer's real queue_state.json.
                win._persist_enabled = False
                win._queue_state_path = os.path.join(tmp, "queue_state.json")
                if win.queue:
                    win.queue.clear_all()
                    win._rebuild_queue_table()
                win._persist_enabled = True

                # Clear All button exists next to Clear Finished wiring.
                from PyQt6.QtWidgets import QPushButton

                clear_all_btns = [
                    b for b in win.findChildren(QPushButton) if b.text() == "Clear All"
                ]
                self.assertTrue(clear_all_btns)

                q = win._ensure_queue()
                q.clear_all()
                win._rebuild_queue_table()
                a = q.add("https://example.com/a")
                b = q.add("https://example.com/b")
                win._upsert_job_row(a)
                win._upsert_job_row(b)
                self.assertEqual(len(q.jobs()), 2)

                # remove via API path used by context menu
                win._remove_queue_jobs([a.id])
                self.assertEqual([j.id for j in q.jobs()], [b.id])
                self.assertNotIn(a.id, win._job_rows)

                # Clear All with confirm mocked to Yes
                with mock.patch(
                    "ytsgui.main_window.QMessageBox.question",
                    return_value=__import__(
                        "PyQt6.QtWidgets", fromlist=["QMessageBox"]
                    ).QMessageBox.StandardButton.Yes,
                ):
                    win._clear_all_queue()
                self.assertEqual(q.jobs(), [])
                snap = load_queue_state(win._queue_state_path)
                self.assertIsNotNone(snap)
                assert snap is not None
                self.assertEqual(snap.get("jobs") or [], [])

                # Force download wiring
                c = q.add("https://example.com/c")
                win._upsert_job_row(c)
                with mock.patch.object(q, "force_download", return_value=True) as fd:
                    win._force_download_jobs([c.id])
                    fd.assert_called_once_with(c.id)
            finally:
                win.close()


if __name__ == "__main__":
    unittest.main()
