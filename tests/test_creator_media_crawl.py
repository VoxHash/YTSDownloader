"""Unit tests for creator_media crawl modes."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ytscore.crawl import CrawlMode, CrawlResult, crawl_creator_media, crawl_profile
from ytscore.creator_media import PLATFORM_ARYION, PLATFORM_MANYVIDS
from ytscore.settings import Settings


class CreatorCrawlTests(unittest.TestCase):
    def test_manyvids_uses_flat_path(self) -> None:
        with patch(
            "ytscore.crawl.crawl_social_flat",
            return_value=CrawlResult(
                urls=["https://www.manyvids.com/Video/1/"],
                mode=CrawlMode.SHALLOW,
                platform=PLATFORM_MANYVIDS,
            ),
        ) as mocked:
            result = crawl_creator_media(
                "https://www.manyvids.com/Video/1/",
                Settings(),
                mode=CrawlMode.SHALLOW,
                limit=5,
                pace_seconds=0,
            )
        mocked.assert_called_once()
        self.assertEqual(result.platform, PLATFORM_MANYVIDS)
        self.assertEqual(result.urls, ["https://www.manyvids.com/Video/1/"])

    def test_aryion_deep_listing(self) -> None:
        with patch(
            "ytscore.crawl.resolve_creator_listing_pages",
            return_value=[
                "https://aryion.com/g4/view/1",
                "https://aryion.com/g4/view/2",
                "https://aryion.com/g4/view/3",
            ],
        ):
            result = crawl_creator_media(
                "https://aryion.com/g4/favorites/faceinthebutt/Pref",
                Settings(cookies_from_browser="brave:Default"),
                mode=CrawlMode.DEEP,
                limit=2,
                pace_seconds=0,
            )
        self.assertEqual(result.platform, PLATFORM_ARYION)
        self.assertEqual(result.tabs_tried, ["listing"])
        self.assertEqual(len(result.urls), 2)

    def test_crawl_profile_routes_aryion(self) -> None:
        with patch(
            "ytscore.crawl.crawl_creator_media",
            return_value=CrawlResult(
                urls=["https://aryion.com/g4/view/9"],
                mode=CrawlMode.SHALLOW,
                platform=PLATFORM_ARYION,
            ),
        ) as mocked:
            result = crawl_profile(
                "https://aryion.com/g4/favorites/faceinthebutt/Pref",
                Settings(),
                mode=CrawlMode.SHALLOW,
                limit=5,
                require_auth=False,
            )
        mocked.assert_called_once()
        self.assertEqual(result.platform, PLATFORM_ARYION)


if __name__ == "__main__":
    unittest.main()
