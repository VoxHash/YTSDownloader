"""Host-side checks for the Android Chaquopy yt-dlp worker module."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "android" / "app" / "src" / "main" / "python" / "yts_dlp_worker.py"


def _load_worker():
    spec = importlib.util.spec_from_file_location("yts_dlp_worker", WORKER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AndroidYtDlpWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not WORKER.is_file():
            raise unittest.SkipTest(f"missing {WORKER}")
        try:
            import yt_dlp  # noqa: F401
        except ImportError as exc:
            raise unittest.SkipTest(f"yt-dlp not installed: {exc}") from exc
        cls.worker = _load_worker()
        cls.system_ffmpeg = shutil.which("ffmpeg")

    def test_format_selector_single_without_ffmpeg(self) -> None:
        fmt = self.worker.format_selector(None)
        self.assertNotIn("+", fmt)
        self.assertEqual(fmt, self.worker.format_selector("/no/such/ffmpeg"))

    def test_format_selector_merge_with_executable_ffmpeg(self) -> None:
        if not self.system_ffmpeg:
            self.skipTest("system ffmpeg not on PATH")
        fmt = self.worker.format_selector(self.system_ffmpeg)
        self.assertIn("bestvideo", fmt)
        self.assertIn("+", fmt)

    def test_resolve_title_real_video(self) -> None:
        # Me at the zoo — stable public short used across smokes.
        title = self.worker.resolve_title("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        self.assertIsInstance(title, str)
        self.assertTrue(title.strip(), "expected a non-empty title from yt-dlp")

    def test_download_json_contract_tmpdir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="yts-android-dl-") as tmp:
            raw = self.worker.download(
                "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                tmp,
                callback=None,
            )
            payload = json.loads(raw)
            self.assertTrue(payload.get("ok"), payload)
            path = Path(payload["path"])
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 1000)
            self.assertTrue(str(payload.get("title") or "").strip())
            self.assertFalse(payload.get("merged"), "no ffmpeg_location → single-file")

    def test_download_merge_with_system_ffmpeg(self) -> None:
        if not self.system_ffmpeg:
            self.skipTest("system ffmpeg not on PATH")
        with tempfile.TemporaryDirectory(prefix="yts-android-merge-") as tmp:
            raw = self.worker.download(
                "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                tmp,
                callback=None,
                ffmpeg_location=self.system_ffmpeg,
            )
            payload = json.loads(raw)
            self.assertTrue(payload.get("ok"), payload)
            self.assertTrue(payload.get("merged"), payload)
            path = Path(payload["path"])
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 1000)
            # Merge path should leave a single playable container (mp4 preferred).
            self.assertIn(path.suffix.lower(), {".mp4", ".mkv", ".webm"})
            self.assertFalse(payload.get("watermarked"), payload)

    def test_apply_watermark_full_frame(self) -> None:
        if not self.system_ffmpeg:
            self.skipTest("system ffmpeg not on PATH")
        wm_asset = (
            ROOT
            / "android"
            / "app"
            / "src"
            / "main"
            / "assets"
            / "watermark"
            / "default_watermark.png"
        )
        if not wm_asset.is_file():
            self.skipTest(f"missing watermark asset {wm_asset}")
        with tempfile.TemporaryDirectory(prefix="yts-android-wm-") as tmp:
            base = Path(tmp) / "base.mp4"
            # Short synthetic clip (no network).
            import subprocess

            proc = None
            for vcodec in ("libx264", "mpeg4"):
                gen = [
                    self.system_ffmpeg,
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=blue:s=320x240:d=1",
                    "-c:v",
                    vcodec,
                    "-pix_fmt",
                    "yuv420p",
                    str(base),
                ]
                proc = subprocess.run(gen, capture_output=True, text=True, check=False)
                if proc.returncode == 0 and base.is_file():
                    break
            self.assertIsNotNone(proc)
            assert proc is not None
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = Path(tmp) / "out_wm.mp4"
            raw = self.worker.apply_watermark(
                str(base),
                str(wm_asset),
                self.system_ffmpeg,
                str(out),
            )
            payload = json.loads(raw)
            self.assertTrue(payload.get("ok"), payload)
            path = Path(payload["path"])
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 1000)

    def test_download_with_watermark_asset(self) -> None:
        if not self.system_ffmpeg:
            self.skipTest("system ffmpeg not on PATH")
        wm_asset = (
            ROOT
            / "android"
            / "app"
            / "src"
            / "main"
            / "assets"
            / "watermark"
            / "default_watermark.png"
        )
        if not wm_asset.is_file():
            self.skipTest(f"missing watermark asset {wm_asset}")
        with tempfile.TemporaryDirectory(prefix="yts-android-dl-wm-") as tmp:
            raw = self.worker.download(
                "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                tmp,
                callback=None,
                ffmpeg_location=self.system_ffmpeg,
                watermark_path=str(wm_asset),
            )
            payload = json.loads(raw)
            self.assertTrue(payload.get("ok"), payload)
            self.assertTrue(payload.get("watermarked"), payload)
            path = Path(payload["path"])
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 1000)
            self.assertTrue(path.name.endswith("_wm.mp4") or "_wm." in path.name, path.name)


if __name__ == "__main__":
    unittest.main()
