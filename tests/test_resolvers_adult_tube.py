"""Unit tests for adult-tube platform detect, URL canonicalize, playlist auth gate."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ytscore.resolvers import (
    PlaylistAuthError,
    detect_platform,
    is_playlist_url,
    private_playlist_needs_cookies,
    resolve_adult_tube,
    resolve_url,
)
from ytscore.settings import Settings, apply_auth_opts
from ytscore.util import canonicalize_media_url


class AdultTubeDetectTests(unittest.TestCase):
    def test_detect_video_and_playlist(self) -> None:
        self.assertEqual(
            detect_platform(
                "https://www.pornhub.com/view_video.php?viewkey=abc123"
            ),
            "adult_tube",
        )
        self.assertEqual(
            detect_platform("https://www.pornhub.com/playlist/12345"),
            "adult_tube",
        )
        self.assertEqual(
            detect_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "youtube",
        )

    def test_playlist_url_helpers(self) -> None:
        self.assertTrue(is_playlist_url("https://www.pornhub.com/playlist/317222141"))
        self.assertFalse(
            is_playlist_url("https://www.pornhub.com/view_video.php?viewkey=abc")
        )
        self.assertTrue(
            private_playlist_needs_cookies(
                "https://www.pornhub.com/playlist/317222141"
            )
        )
        self.assertFalse(
            private_playlist_needs_cookies(
                "https://www.pornhub.com/view_video.php?viewkey=abc"
            )
        )


class CanonicalizeUrlTests(unittest.TestCase):
    def test_unescape_amp_and_https(self) -> None:
        raw = (
            "http://www.pornhub.com/view_video.php?viewkey=65ba08e41523d"
            "&amp;pkey=317222141"
        )
        cleaned = canonicalize_media_url(raw)
        self.assertTrue(cleaned.startswith("https://"))
        self.assertIn("viewkey=65ba08e41523d", cleaned)
        self.assertIn("pkey=317222141", cleaned)
        self.assertNotIn("&amp;", cleaned)


class PlaylistAuthGateTests(unittest.TestCase):
    def test_playlist_without_cookies_raises(self) -> None:
        with self.assertRaises(PlaylistAuthError):
            resolve_adult_tube(
                "https://www.pornhub.com/playlist/317222141",
                Settings(),
                playlist_end=5,
                require_playlist_cookies=True,
            )

    def test_resolve_url_playlist_requires_cookies(self) -> None:
        with self.assertRaises(PlaylistAuthError):
            resolve_url(
                "https://www.pornhub.com/playlist/317222141",
                Settings(),
                playlist_end=5,
            )

    def test_single_video_without_cookies_attempts_flat(self) -> None:
        with patch(
            "ytscore.resolvers.resolve_flat",
            return_value=["https://www.pornhub.com/view_video.php?viewkey=abc"],
        ) as mocked:
            out = resolve_url(
                "https://www.pornhub.com/view_video.php?viewkey=abc",
                Settings(),
                playlist_end=1,
            )
        self.assertEqual(len(out), 1)
        mocked.assert_called_once()

    def test_resolve_flat_respects_playlist_end(self) -> None:
        from ytscore.resolvers import resolve_flat

        fake_entries = [
            {"url": f"http://www.pornhub.com/view_video.php?viewkey=k{i}&amp;pkey=1"}
            for i in range(20)
        ]

        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=False):
                return {"entries": fake_entries}

        with patch("ytscore.resolvers.yt_dlp") as ytdlp:
            ytdlp.YoutubeDL = FakeYDL
            out = resolve_flat(
                "https://www.pornhub.com/playlist/1",
                Settings(cookies_from_browser="brave:Default", impersonate=""),
                playlist_end=5,
            )
        self.assertEqual(len(out), 5)
        self.assertTrue(all(u.startswith("https://") for u in out))
        self.assertTrue(all("&amp;" not in u for u in out))


class ImpersonateOptsTests(unittest.TestCase):
    def test_apply_auth_opts_sets_impersonate_when_configured(self) -> None:
        opts = apply_auth_opts({}, Settings(impersonate="chrome"))
        self.assertIn("impersonate", opts)
        self.assertEqual(str(opts["impersonate"]).split(":")[0], "chrome")

    def test_apply_auth_opts_skips_empty_impersonate(self) -> None:
        opts = apply_auth_opts({}, Settings(impersonate=""))
        self.assertNotIn("impersonate", opts)


if __name__ == "__main__":
    unittest.main()
