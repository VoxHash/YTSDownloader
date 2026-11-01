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
    _find_next_page,
    aryion_data_php_url,
    creator_listing_max_pages,
    creator_media_id,
    extension_from_content_disposition,
    extension_from_content_type,
    extract_aryion_media_url,
    extract_clips4sale_preview_url,
    guess_direct_extension,
    harvest_aryion_views,
    harvest_clips4sale_clips,
    harvest_fapello_media,
    harvest_pornpics_media,
    is_aryion_listing_url,
    is_aryion_single_url,
    is_clips4sale_listing_url,
    is_clips4sale_single_url,
    listing_query_page,
    media_payload_mismatches_extension,
    needs_direct_cdn_download,
    parse_listing_page_of,
    resolve_listing_pages,
    with_listing_query_page,
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
        <a href="data.php?id=1316304">download</a>
        """
        media = extract_aryion_media_url(
            html, base_url="https://aryion.com/g4/view/1316304"
        )
        self.assertEqual(media, "https://aryion.com/g4/data.php?id=1316304")
        self.assertEqual(
            aryion_data_php_url("https://aryion.com/g4/view/1316304"),
            "https://aryion.com/g4/data.php?id=1316304",
        )
        self.assertTrue(
            needs_direct_cdn_download(
                "https://aryion.com/g4/view/1316304",
                "https://aryion.com/g4/data.php?id=1316304",
            )
        )


class AryionPaginationTests(unittest.TestCase):
    _PAGENAV = """
    <span class='pagenav'> Page 1 of 294 &bull; <span class='pagejumps'><strong>1</strong>
    <a href='/g4/favorites/faceinthebutt/Belly+Vore?p=2'>2</a>
    <a href='/g4/favorites/faceinthebutt/Belly+Vore?p=3'>3</a>
     ... <a href='/g4/favorites/faceinthebutt/Belly+Vore?p=294'>294</a></span>
     &bull; <a href='/g4/favorites/faceinthebutt/Belly+Vore?p=2'>Next &gt;&gt;</a></span>
    """
    _BASE = "https://aryion.com/g4/favorites/faceinthebutt/Belly+Vore"

    def test_parse_page_of_and_query(self) -> None:
        self.assertEqual(parse_listing_page_of(self._PAGENAV), (1, 294))
        self.assertEqual(parse_listing_page_of(""), (None, None))
        self.assertEqual(listing_query_page(self._BASE), 1)
        self.assertEqual(listing_query_page(self._BASE + "?p=12"), 12)
        self.assertIn("p=2", with_listing_query_page(self._BASE, 2))
        self.assertEqual(creator_listing_max_pages(0), 10000)
        self.assertEqual(creator_listing_max_pages(50), 3)

    def test_find_next_handles_encoded_next(self) -> None:
        nxt = _find_next_page(
            self._PAGENAV, base_url=self._BASE, current_url=self._BASE
        )
        self.assertIsNotNone(nxt)
        assert nxt is not None
        self.assertIn("p=2", nxt)
        last_html = (
            "<span class='pagenav'> Page 294 of 294 &bull; "
            "<span class='pagejumps'><a href='?p=293'>293</a> "
            "<strong>294</strong></span></span>"
        )
        last_url = self._BASE + "?p=294"
        self.assertIsNone(
            _find_next_page(last_html, base_url=last_url, current_url=last_url)
        )

    def test_resolve_listing_pages_walks_query_pages(self) -> None:
        pages = {
            self._BASE: (
                self._PAGENAV
                + '<a href="/g4/view/1">a</a><a href="/g4/view/2">b</a>',
                None,
            ),
            self._BASE + "?p=2": (
                "<span class='pagenav'> Page 2 of 294 &bull; "
                "<a href='?p=3'>Next &gt;&gt;</a></span>"
                '<a href="/g4/view/3">c</a><a href="/g4/view/4">d</a>',
                None,
            ),
            self._BASE + "?p=3": (
                "<span class='pagenav'> Page 3 of 294 </span>"
                '<a href="/g4/view/5">e</a>',
                None,
            ),
        }

        def fake_fetch(url: str, _settings):
            return pages[url]

        sleeps: list[float] = []
        with patch(
            "ytscore.creator_media.fetch_html",
            side_effect=fake_fetch,
        ):
            out = resolve_listing_pages(
                self._BASE,
                Settings(),
                limit=0,
                max_pages=3,
                pace_seconds=0.5,
                sleep_fn=sleeps.append,
            )
        self.assertEqual(len(out), 5)
        self.assertEqual(len(sleeps), 2)
        self.assertTrue(all("/g4/view/" in u for u in out))


class AryionExtensionTests(unittest.TestCase):
    def test_content_type_and_disposition(self) -> None:
        self.assertEqual(extension_from_content_type("application/pdf"), ".pdf")
        self.assertEqual(extension_from_content_type("image/png; charset=binary"), ".png")
        self.assertEqual(
            extension_from_content_type(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            ".docx",
        )
        self.assertEqual(
            extension_from_content_type("application/x-shockwave-flash"),
            ".swf",
        )
        self.assertEqual(
            extension_from_content_disposition(
                'attachment; filename="FairyTaleEater12-1319172-story.pdf"'
            ),
            ".pdf",
        )
        self.assertEqual(
            extension_from_content_disposition(
                "attachment; filename*=UTF-8''RealZikik-1194110-Halloween%20Favor.docx"
            ),
            ".docx",
        )

    def test_guess_direct_extension_url_and_headers(self) -> None:
        self.assertEqual(
            guess_direct_extension(
                "https://aryion.com/g4/data/1319172-134593-1iwpsaw.pdf"
            ),
            ".pdf",
        )
        self.assertEqual(
            guess_direct_extension(
                "https://aryion.com/g4/data/1254924-9242-1qcec2y.doc.html"
            ),
            ".html",
        )
        self.assertEqual(
            guess_direct_extension(
                "https://aryion.com/g4/data.php?id=1254924",
                default=".bin",
                content_type="application/msword",
                content_disposition='attachment; filename="hunnter-1254924-story.doc"',
            ),
            ".doc",
        )
        self.assertEqual(
            guess_direct_extension(
                "https://aryion.com/g4/data.php?id=1",
                default=".mp4",
                content_type="application/pdf",
            ),
            ".pdf",
        )

    def test_payload_mismatch(self) -> None:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            pdf_as_mp4 = os.path.join(tmp, "item [1].mp4")
            with open(pdf_as_mp4, "wb") as handle:
                handle.write(b"%PDF-1.4\n%")
            self.assertTrue(media_payload_mismatches_extension(pdf_as_mp4))
            good = os.path.join(tmp, "item [2].pdf")
            with open(good, "wb") as handle:
                handle.write(b"%PDF-1.4\n%")
            self.assertFalse(media_payload_mismatches_extension(good))
            html_as_mp4 = os.path.join(tmp, "item [3].mp4")
            with open(html_as_mp4, "wb") as handle:
                handle.write(b"<html><head></head></html>")
            self.assertTrue(media_payload_mismatches_extension(html_as_mp4))


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
