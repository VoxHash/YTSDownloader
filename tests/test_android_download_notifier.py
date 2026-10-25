"""Host checks mirroring Android DownloadNotifier helpers (slice 7)."""

from __future__ import annotations

import unittest


def _java_string_hash(s: str) -> int:
    """Java String.hashCode twin used by DownloadNotifier.notifId."""
    h = 0
    for ch in s:
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    if h >= 0x80000000:
        h -= 0x100000000
    if h == -2147483648:
        return 1
    return abs(h) if abs(h) >= 1 else 1


class AndroidDownloadNotifierTests(unittest.TestCase):
    def test_notif_id_stable_and_positive(self) -> None:
        a = _java_string_hash("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        b = _java_string_hash("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        self.assertEqual(a, b)
        self.assertGreaterEqual(a, 1)

    def test_notif_id_case_insensitive_trim(self) -> None:
        a = _java_string_hash("https://example.com/a".strip().lower())
        b = _java_string_hash("  HTTPS://EXAMPLE.COM/A  ".strip().lower())
        self.assertEqual(a, b)

    def test_channel_id_constant_in_source(self) -> None:
        from pathlib import Path

        src = (
            Path(__file__).resolve().parents[1]
            / "android"
            / "app"
            / "src"
            / "main"
            / "java"
            / "dev"
            / "voxhash"
            / "ytscompanion"
            / "DownloadNotifier.kt"
        )
        text = src.read_text(encoding="utf-8")
        self.assertIn('CHANNEL_ID = "yts_downloads"', text)
        self.assertIn("POST_NOTIFICATIONS", text)
        self.assertIn("ensureChannel", text)


if __name__ == "__main__":
    unittest.main()
