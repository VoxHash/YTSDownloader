"""Unit tests for queue JSON serialize/deserialize and restore rules."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from ytscore.persist import (
    RESTORED_MESSAGE,
    deserialize_queue_snapshot,
    job_from_dict,
    job_to_dict,
    load_queue_state,
    normalize_restored_state,
    save_queue_state,
    serialize_queue_snapshot,
)
from ytscore.queue import DownloadQueue, JobState, QueueJob
from ytscore.settings import Settings


class SerializeDeserializeTests(unittest.TestCase):
    def test_job_roundtrip(self) -> None:
        job = QueueJob(
            id="abc-1",
            url="https://example.com/v/1",
            title="Example",
            media="audio",
            state=JobState.FAILED,
            progress=42.5,
            message="boom",
            path="/tmp/out.m4a",
            error="boom",
            index=3,
            search_query=None,
        )
        data = job_to_dict(job)
        restored = job_from_dict(data, remap_running=False)
        self.assertEqual(restored.id, job.id)
        self.assertEqual(restored.url, job.url)
        self.assertEqual(restored.title, job.title)
        self.assertEqual(restored.media, job.media)
        self.assertEqual(restored.state, JobState.FAILED)
        self.assertEqual(restored.progress, 42.5)
        self.assertEqual(restored.path, job.path)
        self.assertEqual(restored.index, 3)

    def test_running_remaps_to_queued(self) -> None:
        state, msg = normalize_restored_state(JobState.RUNNING)
        self.assertEqual(state, JobState.QUEUED)
        self.assertEqual(msg, RESTORED_MESSAGE)

        job = job_from_dict(
            {
                "id": "r1",
                "url": "https://example.com/v/2",
                "title": "Mid",
                "state": "running",
                "progress": 55.0,
                "message": "Downloading…",
            },
            remap_running=True,
        )
        self.assertEqual(job.state, JobState.QUEUED)
        self.assertEqual(job.message, RESTORED_MESSAGE)
        self.assertEqual(job.progress, 55.0)

    def test_terminal_states_preserved(self) -> None:
        for st in (JobState.DONE, JobState.FAILED, JobState.CANCELLED, JobState.QUEUED):
            got, override = normalize_restored_state(st)
            self.assertEqual(got, st)
            self.assertIsNone(override)

    def test_snapshot_file_roundtrip(self) -> None:
        jobs = [
            QueueJob(id="1", url="https://a.example/1", title="A", state=JobState.QUEUED, index=1),
            QueueJob(
                id="2",
                url="https://a.example/2",
                title="B",
                state=JobState.RUNNING,
                progress=10.0,
                index=2,
            ),
            QueueJob(
                id="3",
                url="https://a.example/3",
                title="C",
                state=JobState.DONE,
                progress=100.0,
                path="/tmp/c.mp4",
                index=3,
            ),
        ]
        snap = serialize_queue_snapshot(
            jobs=jobs,
            output_dir="/tmp/yts-out",
            watermark_path="",
            output_format="mp4",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "queue_state.json")
            save_queue_state(path, snap)
            loaded = load_queue_state(path)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            restored, meta = deserialize_queue_snapshot(loaded, remap_running=True)
            self.assertEqual(meta["output_dir"], "/tmp/yts-out")
            self.assertEqual(len(restored), 3)
            self.assertEqual(restored[0].state, JobState.QUEUED)
            self.assertEqual(restored[1].state, JobState.QUEUED)
            self.assertEqual(restored[1].message, RESTORED_MESSAGE)
            self.assertEqual(restored[2].state, JobState.DONE)
            self.assertEqual(restored[2].path, "/tmp/c.mp4")
            # Atomic write leaves no .tmp behind
            self.assertFalse(os.path.exists(path + ".tmp"))
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
            self.assertEqual(raw["version"], 1)


class QueueRestoreTests(unittest.TestCase):
    def test_restore_jobs_and_clear_terminal(self) -> None:
        q = DownloadQueue(settings=Settings(), output_dir="/tmp/yts-test-out")
        jobs = [
            QueueJob(id="a", url="https://a.example/1", state=JobState.QUEUED, index=1),
            QueueJob(id="b", url="https://a.example/2", state=JobState.DONE, index=2),
            QueueJob(id="c", url="https://a.example/3", state=JobState.FAILED, index=3),
        ]
        q.restore_jobs(jobs)
        self.assertEqual([j.id for j in q.jobs()], ["a", "b", "c"])
        removed = q.clear_terminal()
        self.assertEqual(removed, 2)
        remaining = q.jobs()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].id, "a")
        self.assertEqual(q._counter, 3)


if __name__ == "__main__":
    unittest.main()
