"""Host checks mirroring Android CookieBundle Netscape validation + domain summary (slice 6/7)."""

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


def _extract_domains(lines: list[str]) -> dict[str, int]:
    """Python twin of CookieBundle.extractDomains."""
    counts: dict[str, int] = {}
    for line in lines:
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        parts = t.split("\t")
        if len(parts) < 6:
            continue
        raw = parts[0].strip()
        if not raw:
            continue
        domain = raw.lstrip(".").lower()
        if not domain:
            continue
        counts[domain] = counts.get(domain, 0) + 1
    return counts


def _format_summary(file_name: str, byte_length: int, lines: list[str], top_n: int = 4) -> str:
    """Python twin of CookieBundle.formatSummary."""
    domains = _extract_domains(lines)
    cookie_rows = sum(domains.values())
    unique = len(domains)
    top = sorted(domains.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
    if unique == 0:
        domain_part = "0 domains"
    else:
        listed = ", ".join(f"{d}×{n}" for d, n in top)
        more = unique - len(top)
        more_suffix = f" +{more} more" if more > 0 else ""
        domain_part = f"{unique} domain(s): {listed}{more_suffix}"
    return f"{file_name} · {cookie_rows} cookie row(s) · {domain_part} · {byte_length} B"


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

    def test_extract_domains_counts_and_strips_dot(self) -> None:
        lines = [
            "# Netscape HTTP Cookie File",
            ".youtube.com\tTRUE\t/\tFALSE\t0\ta\t1",
            ".youtube.com\tTRUE\t/\tFALSE\t0\tb\t2",
            "google.com\tFALSE\t/\tTRUE\t0\tc\t3",
            "# comment",
            "bad",
        ]
        domains = _extract_domains(lines)
        self.assertEqual(domains["youtube.com"], 2)
        self.assertEqual(domains["google.com"], 1)
        self.assertEqual(len(domains), 2)

    def test_format_summary_includes_top_domains(self) -> None:
        lines = [
            "# Netscape HTTP Cookie File",
            ".youtube.com\tTRUE\t/\tFALSE\t0\ta\t1",
            ".youtube.com\tTRUE\t/\tFALSE\t0\tb\t2",
            ".youtube.com\tTRUE\t/\tFALSE\t0\tc\t3",
            "google.com\tFALSE\t/\tTRUE\t0\td\t4",
            ".example.org\tTRUE\t/\tFALSE\t0\te\t5",
        ]
        summary = _format_summary("cookies.txt", 128, lines)
        self.assertIn("5 cookie row(s)", summary)
        self.assertIn("3 domain(s)", summary)
        self.assertIn("youtube.com×3", summary)
        self.assertIn("128 B", summary)


if __name__ == "__main__":
    unittest.main()
