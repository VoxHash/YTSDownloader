"""Unit tests for export presets and queue apply / persist fields."""

from __future__ import annotations

import os
import tempfile
import unittest

from ytscore.persist import deserialize_queue_snapshot, job_from_dict, job_to_dict, serialize_queue_snapshot
from ytscore.presets import (
    AUDIO_ONLY,
    CUSTOM,
    VIDEO_AUDIO,
    WATERMARK,
    apply_preset_to_jobs,
    get_preset,
    list_presets,
    resolve_job_options,
)
from ytscore.queue import DownloadQueue, JobState, QueueJob
from ytscore.settings import Settings


class PresetCatalogTests(unittest.TestCase):
    def test_builtin_ids(self) -> None:
        ids = {p.id for p in list_presets(include_custom=True)}
        self.assertEqual(ids, {"audio_only", "video_audio", "watermark", "custom"})
        self.assertNotIn("custom", {p.id for p in list_presets(include_custom=False)})

    def test_get_preset(self) -> None:
        self.assertIs(get_preset("audio_only"), AUDIO_ONLY)
        self.assertIsNone(get_preset("nope"))


class ResolveOptionsTests(unittest.TestCase):
    def test_audio_only_clears_watermark(self) -> None:
        opts = resolve_job_options(AUDIO_ONLY, watermark_path="/tmp/wm.png", output_format="mp4")
        self.assertEqual(opts["media"], "audio")
        self.assertEqual(opts["watermark_path"], "")

    def test_video_audio_clears_watermark(self) -> None:
        opts = resolve_job_options(VIDEO_AUDIO, watermark_path="/tmp/wm.png")
        self.assertEqual(opts["media"], "video")
        self.assertEqual(opts["output_format"], "mp4")
        self.assertEqual(opts["watermark_path"], "")

    def test_watermark_keeps_path(self) -> None:
        opts = resolve_job_options(WATERMARK, watermark_path="/tmp/wm.png", output_format="webm")
        self.assertEqual(opts["media"], "video")
        self.assertEqual(opts["watermark_path"], "/tmp/wm.png")
        self.assertEqual(opts["output_format"], "webm")

    def test_custom_uses_overrides(self) -> None:
        opts = resolve_job_options(
            CUSTOM,
            watermark_path="/tmp/w.png",
            output_format="mkv",
            media_override="video",
        )
        self.assertEqual(opts["media"], "video")
        self.assertEqual(opts["output_format"], "mkv")
        self.assertEqual(opts["watermark_path"], "/tmp/w.png")


class ApplyPresetToJobsTests(unittest.TestCase):
    def test_skips_search_audio(self) -> None:
        jobs = [
            QueueJob(id="1", url="https://a.example/1", media="video"),
            QueueJob(id="2", url="https://a.example/2", media="search_audio", search_query="q"),
        ]
        n = apply_preset_to_jobs(jobs, AUDIO_ONLY)
        self.assertEqual(n, 1)
        self.assertEqual(jobs[0].media, "audio")
        self.assertEqual(jobs[1].media, "search_audio")

    def test_queue_apply_export_options(self) -> None:
        q = DownloadQueue(settings=Settings(), output_dir="/tmp/yts-preset-out")
        a = q.add("https://a.example/1", media="video", watermark_path="", output_format="mp4")
        b = q.add("https://a.example/2", media="video", watermark_path="", output_format="mp4")
        c = q.add(
            "https://a.example/3",
            media="search_audio",
            title="q",
            search_query="q",
        )
        n = q.apply_export_options(
            [a.id, b.id, c.id],
            media="audio",
            watermark_path="",
            output_format="m4a",
        )
        self.assertEqual(n, 2)
        self.assertEqual(q.get(a.id).media, "audio")
        self.assertEqual(q.get(b.id).media, "audio")
        self.assertEqual(q.get(c.id).media, "search_audio")

        n2 = q.apply_export_options(
            None,
            media="video",
            watermark_path="/tmp/wm.png",
            output_format="mp4",
            only_states=[JobState.QUEUED],
        )
        self.assertEqual(n2, 2)
        self.assertEqual(q.get(a.id).watermark_path, "/tmp/wm.png")


class PersistPresetFieldsTests(unittest.TestCase):
    def test_job_roundtrip_export_fields(self) -> None:
        job = QueueJob(
            id="p1",
            url="https://example.com/v",
            media="video",
            watermark_path="/tmp/wm.png",
            output_format="webm",
        )
        restored = job_from_dict(job_to_dict(job), remap_running=False)
        self.assertEqual(restored.watermark_path, "/tmp/wm.png")
        self.assertEqual(restored.output_format, "webm")

    def test_legacy_jobs_inherit_none(self) -> None:
        job = job_from_dict(
            {"id": "old", "url": "https://example.com/old", "media": "video", "state": "queued"},
            remap_running=False,
        )
        self.assertIsNone(job.watermark_path)
        self.assertIsNone(job.output_format)

    def test_snapshot_includes_export_fields(self) -> None:
        jobs = [
            QueueJob(
                id="1",
                url="https://a.example/1",
                media="audio",
                watermark_path="",
                output_format="m4a",
                index=1,
            )
        ]
        snap = serialize_queue_snapshot(
            jobs=jobs,
            output_dir="/tmp/out",
            watermark_path="",
            output_format="mp4",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "q.json")
            from ytscore.persist import save_queue_state, load_queue_state

            save_queue_state(path, snap)
            loaded = load_queue_state(path)
            restored, _meta = deserialize_queue_snapshot(loaded)
            self.assertEqual(restored[0].media, "audio")
            self.assertEqual(restored[0].output_format, "m4a")
            self.assertEqual(restored[0].watermark_path, "")


class PresetUiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def test_download_preset_combo_and_apply(self) -> None:
        from ytsgui.main_window import SuiteWindow

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            from ytscore.settings import save_settings

            save_settings(Settings(theme="SuiteDark", cookies_from_browser="brave:Default"), path)
            win = SuiteWindow(settings=Settings(theme="SuiteDark"), config_path=path)
            try:
                self.assertGreaterEqual(win.preset_combo.count(), 3)
                # Select Audio only
                idx = win.preset_combo.findData("audio_only")
                self.assertGreaterEqual(idx, 0)
                win.preset_combo.setCurrentIndex(idx)
                self.assertTrue(win.media_audio.isChecked())
                opts = win._current_enqueue_options()
                self.assertEqual(opts["media"], "audio")
                self.assertEqual(opts["watermark_path"], "")

                # Queue a fake job and apply Video + audio via queue controls
                q = win._ensure_queue()
                job = q.add(
                    "https://example.com/smoke",
                    media="audio",
                    watermark_path="",
                    output_format="m4a",
                )
                win._upsert_job_row(job)
                qidx = win.queue_preset_combo.findData("video_audio")
                win.queue_preset_combo.setCurrentIndex(qidx)
                n = q.apply_export_options(
                    [job.id],
                    media="video",
                    watermark_path="",
                    output_format="mp4",
                )
                self.assertEqual(n, 1)
                self.assertEqual(q.get(job.id).media, "video")
            finally:
                win.close()


if __name__ == "__main__":
    unittest.main()
