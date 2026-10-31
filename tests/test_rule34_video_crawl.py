"""Unit tests for rule34_video crawl modes and paced listing harvest."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ytscore.crawl import CrawlMode, crawl_profile
from ytscore.rule34_video import PLATFORM_ID
from ytscore.settings import Settings


class Rule34VideoCrawlTests(unittest.TestCase):
    def test_single_shallow(self) -> None:
        result = crawl_profile(
            "https://rule34video.com/video/3065157/shot-it/",
            Settings(),
            mode=CrawlMode.SHALLOW,
            limit=5,
            require_auth=False,
        )
        self.assertEqual(result.platform, PLATFORM_ID)
        self.assertEqual(len(result.urls), 1)
        self.assertIn("/video/3065157/shot-it/", result.urls[0])

    def test_deep_listing_paginates(self) -> None:
        settings = Settings()
        settings.cookies_from_browser = "brave:Default"
        with patch(
            "ytscore.crawl.resolve_listing_pages",
            return_value=[
                "https://rule34video.com/video/1/a/",
                "https://rule34video.com/video/2/b/",
                "https://rule34video.com/video/3/c/",
            ],
        ) as mocked:
            result = crawl_profile(
                "https://rule34video.com/latest-updates/",
                settings,
                mode=CrawlMode.DEEP,
                limit=3,
                pace_seconds=0,
                require_auth=True,
            )
        self.assertEqual(result.platform, PLATFORM_ID)
        self.assertEqual(result.urls, mocked.return_value)
        mocked.assert_called_once()
        self.assertIn("listing", result.tabs_tried)

    def test_deep_requires_cookies(self) -> None:
        from ytscore.crawl import CrawlAuthError

        with self.assertRaises(CrawlAuthError):
            crawl_profile(
                "https://rule34video.com/tags/3065/",
                Settings(),
                mode=CrawlMode.DEEP,
                limit=5,
                require_auth=True,
            )


if __name__ == "__main__":
    unittest.main()
