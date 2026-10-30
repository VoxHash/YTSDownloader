"""Unit tests for resilient yt-dlp video format selection / fallback."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from ytscore.formats import (
    DEFAULT_VIDEO_FORMAT,
    RESILIENT_VIDEO_FORMAT,
    is_format_unavailable_error,
    next_format_fallback,
    normalize_video_format,
)
from ytscore.settings import Settings, apply_auth_opts, resolve_js_runtime_path


class FormatHelpersTests(unittest.TestCase):
    def test_normalize_upgrades_legacy_default(self) -> None:
        self.assertEqual(
            normalize_video_format("bestvideo+bestaudio/best"),
            DEFAULT_VIDEO_FORMAT,
        )
        self.assertEqual(normalize_video_format(""), DEFAULT_VIDEO_FORMAT)

    def test_normalize_keeps_custom(self) -> None:
        custom = "bv*[height<=1080]+ba/b"
        self.assertEqual(normalize_video_format(custom), custom)

    def test_format_unavailable_detection(self) -> None:
        msg = (
            "ERROR: [youtube] iT3YPqxlraU: Requested format is not available. "
            "Use --list-formats for a list of available formats"
        )
        self.assertTrue(is_format_unavailable_error(msg))
        self.assertTrue(is_format_unavailable_error(Exception(msg)))
        self.assertFalse(is_format_unavailable_error("HTTP Error 403: Forbidden"))

    def test_next_format_fallback_chain(self) -> None:
        self.assertEqual(
            next_format_fallback("bestvideo+bestaudio/best"),
            RESILIENT_VIDEO_FORMAT,
        )
        self.assertEqual(
            next_format_fallback("worst"),
            RESILIENT_VIDEO_FORMAT,
        )
        self.assertIsNone(next_format_fallback(RESILIENT_VIDEO_FORMAT))
        self.assertIsNone(next_format_fallback(DEFAULT_VIDEO_FORMAT))


class JsRuntimeResolveTests(unittest.TestCase):
    def test_explicit_path_preferred(self) -> None:
        with tempfile.NamedTemporaryFile(prefix="fake-node-", delete=False) as fh:
            path = fh.name
        try:
            os.chmod(path, 0o755)
            resolved = resolve_js_runtime_path("node", path)
            self.assertEqual(resolved, path)
        finally:
            os.unlink(path)

    def test_apply_auth_opts_sets_js_path_when_resolvable(self) -> None:
        with tempfile.NamedTemporaryFile(prefix="fake-node-", delete=False) as fh:
            path = fh.name
        try:
            os.chmod(path, 0o755)
            opts = apply_auth_opts(
                {},
                Settings(js_runtime="node", js_runtime_path=path, impersonate=""),
            )
            self.assertEqual(opts["js_runtimes"], {"node": {"path": path}})
        finally:
            os.unlink(path)

    def test_apply_auth_opts_falls_back_to_empty_dict_when_missing(self) -> None:
        with mock.patch("ytscore.settings.resolve_js_runtime_path", return_value=None):
            opts = apply_auth_opts(
                {},
                Settings(js_runtime="node", js_runtime_path="", impersonate=""),
            )
        self.assertEqual(opts["js_runtimes"], {"node": {}})


class DownloadFormatFallbackTests(unittest.TestCase):
    def test_download_retries_with_resilient_format(self) -> None:
        from ytscore import downloader as dl

        calls: list[str] = []
        brittle = "bestvideo[height=99999]+bestaudio"

        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=True):
                fmt = self.opts.get("format") or ""
                calls.append(fmt)
                if fmt == brittle:
                    raise Exception(
                        "ERROR: [youtube] x: Requested format is not available. "
                        "Use --list-formats for a list of available formats"
                    )
                return {"title": "ok", "id": "x"}

        settings = Settings(
            video_format_pref=brittle,
            max_retries=0,
            impersonate="",
            js_runtime="",
            skip_existing=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            # Touch a file so _find_download succeeds.
            with open(os.path.join(tmp, "0001_ok [x].mp4"), "wb") as fh:
                fh.write(b"x" * 64)
            with mock.patch.object(dl, "yt_dlp") as fake_mod, mock.patch.object(
                dl, "apply_auth_opts", side_effect=lambda o, s: o
            ):
                fake_mod.YoutubeDL = FakeYDL
                result = dl.download_item(
                    "https://www.youtube.com/watch?v=x",
                    tmp,
                    settings,
                    media="video",
                    index=1,
                    output_format="mp4",
                )
        self.assertTrue(result.ok, result.error)
        self.assertEqual(calls, [brittle, RESILIENT_VIDEO_FORMAT])

    def test_legacy_pref_normalized_before_first_attempt(self) -> None:
        from ytscore import downloader as dl

        captured: list[dict] = []

        class FakeYDL:
            def __init__(self, opts):
                captured.append(dict(opts))

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=True):
                return {"title": "t", "id": "id"}

        settings = Settings(
            video_format_pref="bestvideo+bestaudio/best",
            max_retries=0,
            impersonate="",
            js_runtime="",
            skip_existing=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "ok [id].mp4"), "wb") as fh:
                fh.write(b"data")
            with mock.patch.object(dl, "yt_dlp") as fake_mod, mock.patch.object(
                dl, "apply_auth_opts", side_effect=lambda o, s: o
            ):
                fake_mod.YoutubeDL = FakeYDL
                result = dl.download_item(
                    "https://example.com/v",
                    tmp,
                    settings,
                    media="video",
                )
        self.assertTrue(result.ok, result.error)
        self.assertEqual(captured[0]["format"], DEFAULT_VIDEO_FORMAT)
        self.assertIn("format_sort", captured[0])


if __name__ == "__main__":
    unittest.main()
