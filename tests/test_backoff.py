"""Unit tests for rate-limit detection and exponential backoff (no live hosts)."""

from __future__ import annotations

import time
import unittest
from unittest import mock

from ytscore.backoff import (
    compute_backoff_seconds,
    is_rate_limited,
    is_retryable_temporary,
)
from ytscore.downloader import DownloadResult, download_item
from ytscore.queue import DownloadQueue, JobState
from ytscore.settings import Settings, load_settings


class BackoffMathTests(unittest.TestCase):
    def test_exponential_series(self) -> None:
        self.assertEqual(compute_backoff_seconds(1, base=2, factor=2, maximum=90), 2.0)
        self.assertEqual(compute_backoff_seconds(2, base=2, factor=2, maximum=90), 4.0)
        self.assertEqual(compute_backoff_seconds(3, base=2, factor=2, maximum=90), 8.0)
        self.assertEqual(compute_backoff_seconds(10, base=2, factor=2, maximum=90), 90.0)

    def test_rate_limited_uses_harder_base(self) -> None:
        normal = compute_backoff_seconds(1, base=2, factor=2, maximum=90, rate_limited=False)
        hard = compute_backoff_seconds(1, base=2, factor=2, maximum=90, rate_limited=True)
        self.assertEqual(normal, 2.0)
        self.assertEqual(hard, 4.0)
        self.assertGreater(
            compute_backoff_seconds(3, base=2, factor=2, maximum=90, rate_limited=True),
            compute_backoff_seconds(3, base=2, factor=2, maximum=90, rate_limited=False),
        )


class RateLimitDetectionTests(unittest.TestCase):
    def test_detects_429_and_phrases(self) -> None:
        self.assertTrue(is_rate_limited("HTTP Error 429: Too Many Requests"))
        self.assertTrue(is_rate_limited(RuntimeError("rate-limit exceeded")))
        self.assertTrue(is_rate_limited("please slow down"))
        self.assertFalse(is_rate_limited("Video unavailable"))
        self.assertFalse(is_rate_limited(None))

    def test_temporary_includes_5xx_and_timeouts(self) -> None:
        self.assertTrue(is_retryable_temporary("HTTP Error 503: Service Unavailable"))
        self.assertTrue(is_retryable_temporary("Connection reset by peer"))
        self.assertTrue(is_retryable_temporary("extractor error: timed out"))
        self.assertFalse(is_retryable_temporary("Private video"))


class SettingsLoadTests(unittest.TestCase):
    def test_load_backoff_defaults_from_config(self) -> None:
        s = load_settings("config.ini")
        self.assertGreaterEqual(s.pace_seconds, 2.0)
        self.assertEqual(s.backoff_base, 2.0)
        self.assertEqual(s.backoff_factor, 2.0)
        self.assertEqual(s.backoff_max, 90.0)


class DownloadRetryBackoffTests(unittest.TestCase):
    def test_retry_sleeps_exponential_on_failure(self) -> None:
        settings = Settings(max_retries=2, backoff_base=1.0, backoff_factor=2.0, backoff_max=30.0)
        sleeps: list[float] = []

        def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)

        class Boom:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=True):
                raise RuntimeError("HTTP Error 429: Too Many Requests")

        fake_yt = mock.Mock()
        fake_yt.YoutubeDL.side_effect = lambda opts: Boom()
        with mock.patch("ytscore.downloader._require_yt_dlp", return_value=fake_yt), \
             mock.patch("ytscore.downloader.time.sleep", side_effect=fake_sleep), \
             mock.patch("ytscore.downloader.os.makedirs"):
            result = download_item(
                "https://example.com/watch?v=x",
                "/tmp/yts-test-out",
                settings,
                media="video",
            )
        self.assertFalse(result.ok)
        self.assertTrue(result.rate_limited)
        # attempts = 3 → two sleeps: rate-limited base 2× → 2.0 then 4.0
        self.assertEqual(sleeps, [2.0, 4.0])


class QueuePaceSlotTests(unittest.TestCase):
    def test_start_slots_are_spaced(self) -> None:
        settings = Settings(pace_seconds=0.15, max_workers=2, max_retries=0)
        q = DownloadQueue(settings=settings, output_dir="/tmp/yts-test-out")
        starts: list[float] = []
        lock = __import__("threading").Lock()

        def fake_download(*args, **kwargs):
            with lock:
                starts.append(time.monotonic())
            time.sleep(0.02)
            return DownloadResult(ok=True, path=None, title="ok")

        with mock.patch("ytscore.queue.download_item", side_effect=fake_download):
            q.add_many(["https://a.example/1", "https://a.example/2", "https://a.example/3"])
            q.start()
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                states = {j.state for j in q.jobs()}
                if states <= {JobState.DONE, JobState.FAILED} and len(starts) == 3:
                    break
                time.sleep(0.05)
            q.stop()

        self.assertEqual(len(starts), 3)
        gaps = [starts[i + 1] - starts[i] for i in range(len(starts) - 1)]
        for gap in gaps:
            self.assertGreaterEqual(gap, 0.12, msg=f"gap {gap} too small; starts={starts}")


if __name__ == "__main__":
    unittest.main()
