"""Unit tests for rule34_video platform detect, resolve, and listing harvest."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ytscore.resolvers import detect_platform, resolve_rule34_video, resolve_url
from ytscore.rule34_video import (
    PLATFORM_ID,
    extract_media_formats,
    find_next_listing_page,
    harvest_listing_videos,
    is_rule34_video_listing_url,
    is_rule34_video_single_url,
    rule34_video_id,
    select_best_media_url,
)
from ytscore.settings import Settings


class Rule34VideoDetectTests(unittest.TestCase):
    def test_detect_platform(self) -> None:
        self.assertEqual(
            detect_platform("https://rule34video.com/video/3065157/shot-it-mmd-hmv/"),
            PLATFORM_ID,
        )
        self.assertEqual(
            detect_platform("https://www.rule34video.com/videos/3065157/x/"),
            PLATFORM_ID,
        )
        self.assertEqual(
            detect_platform("https://rule34video.com/tags/3065/"),
            PLATFORM_ID,
        )
        self.assertEqual(
            detect_platform("https://rule34video.com/members/22119/"),
            PLATFORM_ID,
        )
        self.assertNotEqual(
            detect_platform("https://www.pornhub.com/view_video.php?viewkey=abc"),
            PLATFORM_ID,
        )

    def test_url_helpers(self) -> None:
        single = "https://rule34video.com/video/3065157/shot-it/"
        self.assertTrue(is_rule34_video_single_url(single))
        self.assertEqual(rule34_video_id(single), "3065157")
        self.assertTrue(
            is_rule34_video_listing_url("https://rule34video.com/latest-updates/")
        )
        self.assertTrue(
            is_rule34_video_listing_url("https://rule34video.com/search/?q=mmd")
        )
        self.assertFalse(is_rule34_video_listing_url(single))


class HarvestAndFormatsTests(unittest.TestCase):
    def test_harvest_listing_videos(self) -> None:
        html = """
        <a href="/video/111/one/">a</a>
        <a href="https://rule34video.com/videos/222/two/">b</a>
        <a href="/tags/9/">noise</a>
        """
        urls = harvest_listing_videos(
            html, base_url="https://rule34video.com/latest-updates/", limit=10
        )
        self.assertEqual(len(urls), 2)
        self.assertTrue(urls[0].endswith("/video/111/one/"))
        self.assertIn("/videos/222/two/", urls[1])

    def test_extract_formats_prefers_highest(self) -> None:
        html = """
        var flashvars = {
          video_url: 'https://rule34video.com/get_file/1/a/360.mp4/?t=1',
          video_url_text: '360p',
          video_alt_url: 'https://rule34video.com/get_file/1/b/1080p.mp4/?t=1',
          video_alt_url_text: '1080p',
        };
        <a href="https://rule34video.com/get_file/1/c/720p.mp4/?download=true">dl</a>
        """
        formats = extract_media_formats(html, base_url="https://rule34video.com/")
        best = select_best_media_url(formats)
        self.assertIn("1080p", best)

    def test_find_next_listing_page(self) -> None:
        html = """
        <div id="pagination">
          <a href="/latest-updates/" data-parameters="sort_by:post_date;from:01">01</a>
          <a href="/latest-updates/2/" data-parameters="sort_by:post_date;from:02">02</a>
        </div>
        """
        nxt = find_next_listing_page(
            html,
            base_url="https://rule34video.com/latest-updates/",
            current_url="https://rule34video.com/latest-updates/",
        )
        self.assertIsNotNone(nxt)
        self.assertIn("/latest-updates/2/", nxt or "")


class ResolveRule34VideoTests(unittest.TestCase):
    def test_single_normalizes_path(self) -> None:
        out = resolve_rule34_video(
            "https://rule34video.com/videos/3065157/shot-it-mmd-hmv/",
            Settings(),
            playlist_end=1,
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(
            out[0],
            "https://rule34video.com/video/3065157/shot-it-mmd-hmv/",
        )

    def test_listing_uses_harvest(self) -> None:
        with patch(
            "ytscore.resolvers.resolve_listing_pages",
            return_value=[
                "https://rule34video.com/video/1/a/",
                "https://rule34video.com/video/2/b/",
            ],
        ) as mocked:
            out = resolve_url(
                "https://rule34video.com/tags/3065/",
                Settings(),
                playlist_end=5,
            )
        self.assertEqual(len(out), 2)
        mocked.assert_called_once()


if __name__ == "__main__":
    unittest.main()
