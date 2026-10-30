"""Unit + offscreen smoke tests for cookie-gated profile crawl modes."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ytscore.crawl import (
    CRAWL_LIMIT_MAX,
    CRAWL_MODE_LABELS,
    CrawlAuthError,
    CrawlMode,
    clamp_crawl_limit,
    cookie_auth_configured,
    crawl_budget_exhausted,
    crawl_many,
    crawl_profile,
    crawl_requires_auth,
    parse_crawl_mode,
    remaining_crawl_budget,
    take_crawl_budget,
)
from ytscore.queue import JobState
from ytscore.settings import Settings, load_settings, save_settings


class CrawlHelpersTests(unittest.TestCase):
    def test_cookie_auth_browser(self) -> None:
        self.assertTrue(
            cookie_auth_configured(Settings(cookies_from_browser="brave:Default"))
        )
        self.assertTrue(
            cookie_auth_configured(Settings(cookies_file="/tmp/cookies.txt"))
        )
        self.assertFalse(cookie_auth_configured(Settings()))

    def test_crawl_requires_auth(self) -> None:
        self.assertFalse(crawl_requires_auth(CrawlMode.SHALLOW))
        for mode in (
            CrawlMode.DEEP,
            CrawlMode.VIDEOS,
            CrawlMode.SHORTS,
            CrawlMode.POSTS,
        ):
            self.assertTrue(crawl_requires_auth(mode))

    def test_parse_and_clamp(self) -> None:
        self.assertEqual(parse_crawl_mode("deep"), CrawlMode.DEEP)
        self.assertEqual(parse_crawl_mode(CrawlMode.POSTS), CrawlMode.POSTS)
        with self.assertRaises(ValueError):
            parse_crawl_mode("nope")
        self.assertEqual(clamp_crawl_limit(0), 0)  # unlimited
        self.assertEqual(clamp_crawl_limit(9999), 9999)
        self.assertEqual(clamp_crawl_limit(12000), CRAWL_LIMIT_MAX)
        self.assertEqual(clamp_crawl_limit(25), 25)
        self.assertEqual(clamp_crawl_limit(5000), 5000)
        self.assertFalse(crawl_budget_exhausted(10, 0))
        self.assertTrue(crawl_budget_exhausted(50, 50))
        self.assertEqual(remaining_crawl_budget(10, 0), 0)
        self.assertEqual(remaining_crawl_budget(10, 50), 40)
        self.assertEqual(take_crawl_budget(["a", "b", "c"], 0), ["a", "b", "c"])
        self.assertEqual(take_crawl_budget(["a", "b", "c"], 2), ["a", "b"])

    def test_mode_labels_cover_all(self) -> None:
        for mode in CrawlMode:
            self.assertIn(mode, CRAWL_MODE_LABELS)


class CrawlAuthGateTests(unittest.TestCase):
    def test_deep_without_cookies_raises(self) -> None:
        with self.assertRaises(CrawlAuthError):
            crawl_profile(
                "https://www.youtube.com/@example",
                Settings(),
                mode=CrawlMode.DEEP,
                limit=5,
            )

    def test_shallow_without_cookies_ok(self) -> None:
        with patch("ytscore.crawl.resolve_url", return_value=["https://example.com/a"]):
            result = crawl_profile(
                "https://www.youtube.com/@example",
                Settings(),
                mode=CrawlMode.SHALLOW,
                limit=5,
            )
        self.assertEqual(result.urls, ["https://example.com/a"])
        self.assertFalse(result.auth_required)

    def test_spotify_passthrough(self) -> None:
        url = "https://open.spotify.com/playlist/abc"
        result = crawl_profile(
            url,
            Settings(cookies_from_browser="brave:Default"),
            mode=CrawlMode.DEEP,
            limit=10,
        )
        self.assertEqual(result.urls, [url])
        self.assertEqual(result.platform, "spotify")


class CrawlYoutubeDeepTests(unittest.TestCase):
    def test_deep_tabs_paced_and_limited(self) -> None:
        settings = Settings(cookies_from_browser="brave:Default", pace_seconds=0.01)
        sleeps: list[float] = []

        def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)

        def fake_extract(url: str, settings_arg, *, playlist_end: int):
            if url.endswith("/videos"):
                return (
                    [
                        "https://www.youtube.com/watch?v=v1",
                        "https://www.youtube.com/watch?v=v2",
                    ],
                    None,
                )
            if url.endswith("/shorts"):
                return (["https://www.youtube.com/watch?v=s1"], None)
            if url.endswith("/streams"):
                return (["https://www.youtube.com/watch?v=l1"], None)
            return ([], "unexpected")

        with patch("ytscore.crawl._extract_flat_paged", side_effect=fake_extract):
            result = crawl_profile(
                "https://www.youtube.com/@demo",
                settings,
                mode=CrawlMode.DEEP,
                limit=3,
                pace_seconds=0.05,
                sleep_fn=fake_sleep,
            )

        self.assertEqual(
            result.urls,
            [
                "https://www.youtube.com/watch?v=v1",
                "https://www.youtube.com/watch?v=v2",
                "https://www.youtube.com/watch?v=s1",
            ],
        )
        self.assertEqual(result.tabs_tried, ["/videos", "/shorts"])
        self.assertTrue(sleeps)  # paced between tabs
        self.assertEqual(result.mode, CrawlMode.DEEP)

    def test_videos_mode_single_tab(self) -> None:
        settings = Settings(cookies_from_browser="brave:Default")

        def fake_extract(url: str, settings_arg, *, playlist_end: int):
            self.assertTrue(url.endswith("/videos"))
            return (
                [f"https://www.youtube.com/watch?v=x{i}" for i in range(playlist_end)],
                None,
            )

        with patch("ytscore.crawl._extract_flat_paged", side_effect=fake_extract):
            result = crawl_profile(
                "https://www.youtube.com/@demo/about",
                settings,
                mode=CrawlMode.VIDEOS,
                limit=2,
                pace_seconds=0,
                sleep_fn=lambda _s: None,
            )
        self.assertEqual(len(result.urls), 2)
        self.assertEqual(result.tabs_tried, ["/videos"])

    def test_single_watch_url_short_circuits(self) -> None:
        url = "https://www.youtube.com/watch?v=abc123"
        result = crawl_profile(
            url,
            Settings(cookies_from_browser="brave:Default"),
            mode=CrawlMode.DEEP,
            limit=10,
        )
        self.assertEqual(result.urls, [url])

    def test_social_posts_uses_flat(self) -> None:
        settings = Settings(cookies_from_browser="brave:Default")
        with patch(
            "ytscore.crawl._extract_flat_paged",
            return_value=(["https://www.instagram.com/p/1/", "https://www.instagram.com/p/2/"], None),
        ):
            result = crawl_profile(
                "https://www.instagram.com/someone/",
                settings,
                mode=CrawlMode.POSTS,
                limit=10,
                sleep_fn=lambda _s: None,
            )
        self.assertEqual(len(result.urls), 2)
        self.assertEqual(result.platform, "instagram")


class CrawlManyTests(unittest.TestCase):
    def test_merge_dedupe_limit(self) -> None:
        settings = Settings(cookies_from_browser="brave:Default")

        def fake_one(url, settings_arg, **kwargs):
            from ytscore.crawl import CrawlResult

            if "a" in url:
                return CrawlResult(
                    urls=["https://example.com/1", "https://example.com/2"],
                    mode=CrawlMode.SHALLOW,
                    platform="generic",
                )
            return CrawlResult(
                urls=["https://example.com/2", "https://example.com/3"],
                mode=CrawlMode.SHALLOW,
                platform="generic",
            )

        with patch("ytscore.crawl.crawl_profile", side_effect=fake_one):
            result = crawl_many(
                ["https://host/a", "https://host/b"],
                settings,
                mode=CrawlMode.SHALLOW,
                limit=2,
                pace_seconds=0,
                sleep_fn=lambda _s: None,
            )
        self.assertEqual(
            result.urls,
            ["https://example.com/1", "https://example.com/2"],
        )


class CrawlSuiteSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def test_download_page_crawl_controls_and_auth_gate(self) -> None:
        from ytsgui.main_window import SuiteWindow

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            queue_path = os.path.join(tmp, "queue_state.json")
            save_settings(
                Settings(theme="SuiteDark", cookies_from_browser=""),
                path,
            )
            with patch(
                "ytsgui.main_window.default_queue_state_path",
                return_value=queue_path,
            ):
                win = SuiteWindow(settings=load_settings(path), config_path=path)
            try:
                win.show()
                self.assertTrue(hasattr(win, "crawl_mode_combo"))
                self.assertTrue(hasattr(win, "crawl_limit_spin"))
                self.assertEqual(win._selected_crawl_mode(), CrawlMode.SHALLOW)
                self.assertEqual(win._crawl_limit(), 50)

                deep_idx = win.crawl_mode_combo.findData(CrawlMode.DEEP.value)
                self.assertGreaterEqual(deep_idx, 0)
                win.crawl_mode_combo.setCurrentIndex(deep_idx)
                self.assertEqual(win._selected_crawl_mode(), CrawlMode.DEEP)
                self.assertIn("cookie auth", win.crawl_auth_hint.text().lower())

                # Save Brave cookies via Settings form and re-apply.
                win.settings_cookies_browser.setText("brave:Default")
                settings = win._settings_from_form()
                save_settings(settings, path)
                win._apply_settings_runtime(settings)
                self.assertIn("ready", win.crawl_auth_hint.text().lower())

                # Resolve path uses crawl_profile (mocked).
                win.url_edit.setText("https://www.youtube.com/@smoke")
                win.crawl_limit_spin.setValue(2)
                with patch(
                    "ytsgui.main_window.crawl_profile",
                    return_value=MagicMock(
                        urls=[
                            "https://www.youtube.com/watch?v=1",
                            "https://www.youtube.com/watch?v=2",
                        ],
                        tabs_tried=["/videos"],
                        errors=[],
                    ),
                ):
                    win._resolve_and_queue()
                q = win.queue
                self.assertIsNotNone(q)
                assert q is not None
                self.assertEqual(len(q.jobs()), 2)
                self.assertEqual(q.jobs()[0].state, JobState.QUEUED)
            finally:
                win.close()


if __name__ == "__main__":
    unittest.main()
