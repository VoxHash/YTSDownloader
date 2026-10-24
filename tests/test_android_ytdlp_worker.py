"""Host-side checks for the Android Chaquopy yt-dlp worker module."""

from __future__ import annotations

import importlib.util
import json
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


if __name__ == "__main__":
    unittest.main()
