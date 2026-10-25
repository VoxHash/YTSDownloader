"""Unit tests for adult-tube deep crawl (tabs, HTML harvest, media rewrite)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ytscore.adult_tube import (
    TAB_GIFS,
    TAB_PHOTOS,
    TAB_UPLOADS,
    TAB_VIDEOS,
    adult_tube_profile_root,
    adult_tube_tabs_for_mode,
    harvest_album_photos,
    harvest_profile_listing,
    is_adult_tube_profile_url,
    is_adult_tube_single_url,
    resolve_gif_media_url,
    resolve_photo_media_url,
    tab_uses_html_harvest,
)
from ytscore.crawl import CrawlMode, crawl_profile
from ytscore.settings import Settings


class AdultTubeUrlHelpersTests(unittest.TestCase):
    def test_profile_root_and_single(self) -> None:
        profile = "https://www.pornhub.com/model/zoe_ph"
        self.assertTrue(is_adult_tube_profile_url(profile))
        self.assertEqual(
            adult_tube_profile_root("https://www.pornhub.com/model/zoe_ph/videos"),
            profile,
        )
        self.assertEqual(
            adult_tube_profile_root("https://www.pornhub.com/model/zoe_ph/gifs"),
            profile,
        )
        self.assertFalse(is_adult_tube_single_url(profile))
        self.assertTrue(
            is_adult_tube_single_url(
                "https://www.pornhub.com/view_video.php?viewkey=abc"
            )
        )
        self.assertTrue(is_adult_tube_single_url("https://www.pornhub.com/gif/123"))
        self.assertTrue(is_adult_tube_single_url("https://www.pornhub.com/album/9"))
        self.assertTrue(is_adult_tube_single_url("https://www.pornhub.com/photo/1"))

    def test_tabs_for_mode(self) -> None:
        self.assertEqual(
            adult_tube_tabs_for_mode("deep"),
            [TAB_VIDEOS, TAB_UPLOADS, TAB_GIFS, TAB_PHOTOS],
        )
        self.assertEqual(adult_tube_tabs_for_mode("shorts"), [TAB_GIFS])
        self.assertEqual(adult_tube_tabs_for_mode("posts"), [TAB_PHOTOS])
        self.assertTrue(tab_uses_html_harvest(TAB_GIFS))
        self.assertTrue(tab_uses_html_harvest(TAB_PHOTOS))
        self.assertFalse(tab_uses_html_harvest(TAB_VIDEOS))


class HarvestListingTests(unittest.TestCase):
    def test_harvest_gifs_and_albums(self) -> None:
        html = """
        <li id="gif111" class="gifVideoBlock"></li>
        <li id="gif222"></li>
        <a href="/album/333">one</a>
        <div id="albumphoto444"></div>
        <a href="/albums?o=mv">noise</a>
        """
        gifs = harvest_profile_listing(
            html,
            base_url="https://www.pornhub.com/model/x/gifs",
            kinds=["gif"],
            limit=10,
        )
        self.assertEqual(
            gifs,
            [
                "https://www.pornhub.com/gif/111",
                "https://www.pornhub.com/gif/222",
            ],
        )
        albums = harvest_profile_listing(
            html,
            base_url="https://www.pornhub.com/model/x/photos",
            kinds=["album"],
            limit=10,
        )
        self.assertEqual(
            albums,
            [
                "https://www.pornhub.com/album/333",
                "https://www.pornhub.com/album/444",
            ],
        )

    def test_harvest_album_photos(self) -> None:
        html = """
        <a href="/photo/100">a</a>
        <a href="/photo/200">b</a>
        <a href="/photo/100">dup</a>
        """
        photos = harvest_album_photos(
            html, base_url="https://www.pornhub.com/album/9", limit=10
        )
        self.assertEqual(
            photos,
            [
                "https://www.pornhub.com/photo/100",
                "https://www.pornhub.com/photo/200",
            ],
        )


class MediaResolveTests(unittest.TestCase):
    def test_resolve_gif_prefers_id_mp4(self) -> None:
        html = """
        <img data-gif-url="https://cdn.example/pics/gifs/035/144/992/35144992b.gif?x=1"
             src="https://cdn.example/pics/gifs/035/144/992/35144992a.jpg"/>
        <video data-mp4="https://cdn.example/other/999.mp4"></video>
        """
        with patch(
            "ytscore.adult_tube.fetch_html",
            return_value=(html, None),
        ):
            media = resolve_gif_media_url(
                "https://www.pornhub.com/gif/35144992",
                Settings(),
            )
        self.assertIsNotNone(media)
        assert media is not None
        self.assertIn("35144992", media)
        self.assertTrue(media.endswith(".gif?x=1") or ".gif?" in media)

    def test_resolve_photo_og_image(self) -> None:
        html = """
        <meta property="og:image"
              content="https://cdn.example/pics/albums/019/303/581/435957802/original_435957802.jpg"/>
        """
        with patch(
            "ytscore.adult_tube.fetch_html",
            return_value=(html, None),
        ):
            media = resolve_photo_media_url(
                "https://www.pornhub.com/photo/435957802",
                Settings(),
            )
        self.assertEqual(
            media,
            "https://cdn.example/pics/albums/019/303/581/435957802/original_435957802.jpg",
        )


class CrawlAdultTubeDeepTests(unittest.TestCase):
    def test_deep_tabs_paced_videos_then_html(self) -> None:
        settings = Settings(cookies_from_browser="brave:Default", pace_seconds=0.01)
        sleeps: list[float] = []

        def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)

        def fake_flat(url: str, settings_arg, *, playlist_end: int):
            if url.endswith("/videos/upload"):
                return (["https://www.pornhub.com/view_video.php?viewkey=u1"], None)
            if url.endswith("/videos"):
                return (
                    [
                        "https://www.pornhub.com/view_video.php?viewkey=v1",
                        "https://www.pornhub.com/view_video.php?viewkey=v2",
                    ],
                    None,
                )
            return ([], "unexpected flat")

        def fake_html_tab(tab_url: str, settings_arg, *, tab: str, limit: int):
            if tab == TAB_GIFS:
                return (["https://www.pornhub.com/gif/1"], None)
            if tab == TAB_PHOTOS:
                return (["https://www.pornhub.com/album/9"], None)
            return ([], "unexpected html")

        def fake_expand(album_url: str, settings_arg, *, limit: int):
            return (["https://www.pornhub.com/photo/91"], None)

        with (
            patch("ytscore.crawl._extract_flat_paged", side_effect=fake_flat),
            patch(
                "ytscore.crawl._extract_adult_tube_html_tab",
                side_effect=fake_html_tab,
            ),
            patch("ytscore.crawl.expand_album_to_photos", side_effect=fake_expand),
        ):
            result = crawl_profile(
                "https://www.pornhub.com/model/demo",
                settings,
                mode=CrawlMode.DEEP,
                limit=5,
                pace_seconds=0.05,
                sleep_fn=fake_sleep,
            )

        self.assertEqual(
            result.tabs_tried,
            [TAB_VIDEOS, TAB_UPLOADS, TAB_GIFS, TAB_PHOTOS],
        )
        self.assertEqual(
            result.urls,
            [
                "https://www.pornhub.com/view_video.php?viewkey=v1",
                "https://www.pornhub.com/view_video.php?viewkey=v2",
                "https://www.pornhub.com/view_video.php?viewkey=u1",
                "https://www.pornhub.com/gif/1",
                "https://www.pornhub.com/photo/91",
            ],
        )
        self.assertTrue(sleeps)
        self.assertEqual(result.platform, "adult_tube")

    def test_shorts_mode_gifs_only(self) -> None:
        settings = Settings(cookies_from_browser="brave:Default")

        def fake_html_tab(tab_url: str, settings_arg, *, tab: str, limit: int):
            self.assertEqual(tab, TAB_GIFS)
            return (
                [f"https://www.pornhub.com/gif/{i}" for i in range(limit)],
                None,
            )

        with (
            patch(
                "ytscore.crawl._extract_adult_tube_html_tab",
                side_effect=fake_html_tab,
            ),
            patch("ytscore.crawl._extract_flat_paged") as flat,
        ):
            result = crawl_profile(
                "https://www.pornhub.com/model/demo/about",
                settings,
                mode=CrawlMode.SHORTS,
                limit=2,
                pace_seconds=0,
                sleep_fn=lambda _s: None,
            )
        flat.assert_not_called()
        self.assertEqual(result.tabs_tried, [TAB_GIFS])
        self.assertEqual(len(result.urls), 2)

    def test_single_gif_short_circuits(self) -> None:
        url = "https://www.pornhub.com/gif/99"
        result = crawl_profile(
            url,
            Settings(cookies_from_browser="brave:Default"),
            mode=CrawlMode.DEEP,
            limit=10,
        )
        self.assertEqual(result.urls, [url])


if __name__ == "__main__":
    unittest.main()
