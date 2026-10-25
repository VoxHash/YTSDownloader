"""Host checks mirroring Android CookieBundle Netscape validation (slice 6)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


def _validate_netscape(path: Path) -> tuple[bool, str, int]:
    """Python twin of CookieBundle.validateNetscape for host unit tests."""
    if not path.is_file() or path.stat().st_size <= 0:
        return False, "File is empty", 0
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return False, f"Unreadable: {exc}", 0
    if not lines:
        return False, "File is empty", 0
    head = "\n".join(lines[:8]).lower()
    looks = (
        "netscape" in head
        or "http cookie file" in head
        or any(l.strip().startswith("#HttpOnly_") for l in lines)
        or any(
            len(parts) >= 7
            and parts[0]
            and parts[3].upper() in {"TRUE", "FALSE"}
            for l in lines
            for parts in [l.strip().split("\t")]
        )
    )
    if not looks:
        return False, "Not a Netscape cookies.txt", 0
    rows = 0
    for line in lines:
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        if len(t.split("\t")) >= 6:
            rows += 1
    if rows == 0:
        return False, "no cookie rows", 0
    return True, "", rows


class AndroidCookieBundleTests(unittest.TestCase):
    def test_rejects_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "cookies.txt"
            p.write_text("", encoding="utf-8")
            ok, reason, rows = _validate_netscape(p)
            self.assertFalse(ok)
            self.assertEqual(rows, 0)
            self.assertIn("empty", reason.lower())

    def test_rejects_non_netscape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "cookies.txt"
            p.write_text("this is not cookies\njust junk\n", encoding="utf-8")
            ok, reason, _ = _validate_netscape(p)
            self.assertFalse(ok)
            self.assertIn("Netscape", reason)

    def test_accepts_netscape_header_and_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "cookies.txt"
            p.write_text(
                "# Netscape HTTP Cookie File\n"
                ".example.com\tTRUE\t/\tFALSE\t0\tname\tvalue\n",
                encoding="utf-8",
            )
            ok, reason, rows = _validate_netscape(p)
            self.assertTrue(ok, reason)
            self.assertEqual(rows, 1)


if __name__ == "__main__":
    unittest.main()
