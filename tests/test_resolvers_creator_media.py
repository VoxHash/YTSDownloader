"""Unit tests for creator_media platform detect, harvest, and resolve."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ytscore.creator_media import (
    PLATFORM_ARYION,
    PLATFORM_CLIPS4SALE,
    PLATFORM_FAPELLO,
    PLATFORM_MANYVIDS,
    PLATFORM_PORNPICS,
    PLATFORM_REDGIFS,
    PLATFORM_REDDIT,
    PLATFORM_TWITTER,
    PLATFORM_TWPORNSTARS,
    PLATFORM_VIMEO,
    PLATFORM_VK,
    creator_media_id,
    extract_aryion_media_url,
    extract_clips4sale_preview_url,
    harvest_aryion_views,
    harvest_clips4sale_clips,
    harvest_fapello_media,
    harvest_pornpics_media,
    is_aryion_listing_url,
    is_aryion_single_url,
    is_clips4sale_listing_url,
    is_clips4sale_single_url,
)
from ytscore.resolvers import detect_platform, resolve_creator_media, resolve_url
from ytscore.settings import Settings


class CreatorDetectTests(unittest.TestCase):
    def test_detect_platforms(self) -> None:
        cases = [
            ("https://www.manyvids.com/Video/277957/slug/", PLATFORM_MANYVIDS),
            ("https://www.redgifs.com/watch/icyupbeatvolvox", PLATFORM_REDGIFS),
            ("https://vimeo.com/148751763", PLATFORM_VIMEO),
            ("https://vk.com/video-1_2", PLATFORM_VK),
            ("https://www.reddit.com/r/videos/comments/abc123/title/", PLATFORM_REDDIT),
            ("https://x.com/user/status/1234567890", PLATFORM_TWITTER),
            ("https://twitter.com/user/status/1234567890", PLATFORM_TWITTER),
            (
                "https://www.clips4sale.com/studio/169925/34583401/slug",
                PLATFORM_CLIPS4SALE,
            ),
            (
                "https://aryion.com/g4/favorites/faceinthebutt/Pref",
                PLATFORM_ARYION,
            ),
            ("https://fapello.com/some-model/", PLATFORM_FAPELLO),
            ("https://www.pornpics.com/galleries/12345/", PLATFORM_PORNPICS),
            ("https://www.twpornstars.com/videos/99/", PLATFORM_TWPORNSTARS),
        ]
        for url, expected in cases:
            self.assertEqual(detect_platform(url), expected, url)

    def test_media_ids(self) -> None:
        self.assertEqual(
            creator_media_id("https://www.manyvids.com/Video/277957/x/"),
            "277957",
        )
        self.assertEqual(
            creator_media_id("https://www.redgifs.com/watch/IcyUpbeatVolvox"),
            "icyupbeatvolvox",
        )
        self.assertEqual(
            creator_media_id("https://aryion.com/g4/view/1316304"),
            "1316304",
        )
        self.assertEqual(
            creator_media_id(
                "https://www.clips4sale.com/studio/169925/34583401/slug"
            ),
            "34583401",
        )


class AryionHarvestTests(unittest.TestCase):
    def test_url_helpers(self) -> None:
        single = "https://aryion.com/g4/view/1316304"
        listing = "https://aryion.com/g4/favorites/faceinthebutt/Pref"
        self.assertTrue(is_aryion_single_url(single))
        self.assertFalse(is_aryion_listing_url(single))
        self.assertTrue(is_aryion_listing_url(listing))
        self.assertFalse(is_aryion_single_url(listing))

    def test_harvest_views(self) -> None:
        html = """
        <a href="/g4/view/111">a</a>
        <a href="https://aryion.com/g4/view/222/extra">b</a>
        <a href="/g4/user/noise">n</a>
        """
        urls = harvest_aryion_views(
            html, base_url="https://aryion.com/g4/favorites/u/Pref", limit=10
        )
        self.assertEqual(len(urls), 2)
        self.assertTrue(urls[0].endswith("/g4/view/111"))
        self.assertIn("/g4/view/222", urls[1])

    def test_extract_data_media(self) -> None:
        html = """
        <meta property="og:image" content="https://aryion.com/g4/derivative/1-preview.avif"/>
        <img src="//aryion.com/g4/data/1316304-108350-1gv6elx.png/file.png"/>
        """
        media = extract_aryion_media_url(
            html, base_url="https://aryion.com/g4/view/1316304"
        )
        self.assertIn("/g4/data/1316304-", media)


class Clips4SaleHarvestTests(unittest.TestCase):
    def test_url_helpers(self) -> None:
        single = "https://www.clips4sale.com/studio/169925/34583401/my-clip"
        listing = "https://www.clips4sale.com/clips/category/1/FOOT-FETISH"
        self.assertTrue(is_clips4sale_single_url(single))
        self.assertTrue(is_clips4sale_listing_url(listing))
        self.assertFalse(is_clips4sale_listing_url(single))

    def test_harvest_and_preview(self) -> None:
        html = """
        <a data-clipid="34583401"
           href="/studio/169925/34583401/my-sweaty-feet">x</a>
        <a href="/studio/394577/34731439/foot-fantasy">y</a>
        previewUrl: "https://imagecdn.clips4sale.com/accounts99/169925/clips_previews/prev_34583401.mp4"
        """
        urls = harvest_clips4sale_clips(
            html,
            base_url="https://www.clips4sale.com/clips/category/1/FOOT-FETISH",
            limit=10,
        )
        self.assertGreaterEqual(len(urls), 2)
        self.assertTrue(any("34583401" in u for u in urls))
        preview = extract_clips4sale_preview_url(html)
        self.assertIn("prev_34583401.mp4", preview)


class GalleryHarvestTests(unittest.TestCase):
    def test_fapello_and_pornpics(self) -> None:
        fapello_html = """
        <a href="https://fapello.com/model/content/abc.jpg">c</a>
        <img src="https://cdn.fapello.com/photos/shot.jpg"/>
        """
        f_urls = harvest_fapello_media(
            fapello_html, base_url="https://fapello.com/model/", limit=5
        )
        self.assertTrue(f_urls)
        pornpics_html = """
        <img src="https://cdni.pornpics.com/460/7/864/91142320/91142320_138_d6ea.jpg"/>
        """
        p_urls = harvest_pornpics_media(
            pornpics_html, base_url="https://www.pornpics.com/galleries/1/", limit=5
        )
        self.assertEqual(len(p_urls), 1)
        self.assertIn("/1280/", p_urls[0])


class ResolveCreatorTests(unittest.TestCase):
    def test_resolve_aryion_listing_mocked(self) -> None:
        html = '<a href="/g4/view/1">a</a><a href="/g4/view/2">b</a>'
        with patch(
            "ytscore.creator_media.fetch_html",
            return_value=(html, None),
        ):
            out = resolve_creator_media(
                "https://aryion.com/g4/favorites/faceinthebutt/Pref",
                Settings(),
                playlist_end=10,
            )
        self.assertEqual(len(out), 2)
        self.assertTrue(all("/g4/view/" in u for u in out))

    def test_resolve_url_routes_manyvids(self) -> None:
        with patch(
            "ytscore.resolvers.resolve_flat",
            return_value=["https://www.manyvids.com/Video/277957/"],
        ) as mocked:
            out = resolve_url(
                "https://www.manyvids.com/Video/277957/",
                Settings(),
                playlist_end=1,
            )
        mocked.assert_called_once()
        self.assertEqual(out, ["https://www.manyvids.com/Video/277957/"])


if __name__ == "__main__":
    unittest.main()
