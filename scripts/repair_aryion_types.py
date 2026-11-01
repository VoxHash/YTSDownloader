#!/usr/bin/env python3
"""Repair Aryion library files saved with the wrong extension or HTML previews.

Re-downloads originals via ``/g4/data.php?id=`` when on-disk magic disagrees with
the extension (e.g. PDF/HTML/DOCX stored as ``.mp4``). Safe to re-run with
skip-existing once mismatches are cleared.

Usage (fish-safe)::

    .venv/bin/python scripts/repair_aryion_types.py \\
        --dir "/path/to/Aryion" \\
        --listing "https://aryion.com/g4/favorites/USER/Pref"

Do not use shell globs with ``[id]`` in the filename — brackets are character
classes. Match ids with a regex instead.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

# Allow running from repo root without install.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ytscore.backoff import compute_backoff_seconds, is_rate_limited
from ytscore.creator_media import media_payload_mismatches_extension
from ytscore.downloader import download_item
from ytscore.resolvers import resolve_url
from ytscore.settings import Settings, load_settings

_ID_RE = re.compile(r"\[(\d+)\]")


def _iter_mismatched(folder: Path) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for path in sorted(folder.iterdir(), key=lambda p: p.name):
        if not path.is_file():
            continue
        match = _ID_RE.search(path.name)
        if not match:
            continue
        if media_payload_mismatches_extension(str(path)):
            found.append((match.group(1), path))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        required=True,
        help="Aryion library folder to repair",
    )
    parser.add_argument(
        "--listing",
        default="",
        help="Optional favorites/gallery URL to re-fetch missing items after repair",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max items from --listing (default 100; 0 = unlimited harvest cap)",
    )
    parser.add_argument(
        "--pace",
        type=float,
        default=0.0,
        help="Seconds between downloads (default: Settings COUNT_TIMER_ONGOING)",
    )
    args = parser.parse_args()
    folder = Path(args.dir).expanduser()
    folder.mkdir(parents=True, exist_ok=True)

    base = load_settings()
    pace = args.pace or float(getattr(base, "count_timer_ongoing", 2.5) or 2.5)
    settings = Settings(
        **{
            **base.__dict__,
            "overwrite": False,
            "skip_existing": True,
            "number_files": True,
        }
    )

    mismatched = _iter_mismatched(folder)
    print(f"mismatched files: {len(mismatched)}")
    for media_id, path in mismatched:
        head = path.read_bytes()[:8]
        if head.startswith(b"%PDF"):
            target = path.with_suffix(".pdf")
            if target.exists() and target != path:
                path.unlink()
            else:
                path.rename(target)
            print(f"renamed PDF → {target.name}")
            continue
        print(f"remove mismatched {path.name}")
        path.unlink(missing_ok=True)
        view = f"https://aryion.com/g4/view/{media_id}"
        time.sleep(pace)
        result = download_item(view, str(folder), settings, media="video")
        if result.ok and result.path:
            print(f"  repaired → {os.path.basename(result.path)}")
        else:
            print(f"  FAIL {media_id}: {result.error}")

    if args.listing:
        urls = resolve_url(args.listing, settings, playlist_end=args.limit)
        print(f"listing resolved {len(urls)} urls")
        for index, url in enumerate(urls, start=1):
            if index > 1:
                time.sleep(pace)
            result = download_item(
                url, str(folder), settings, media="video", index=index
            )
            if result.ok and result.path and media_payload_mismatches_extension(result.path):
                os.remove(result.path)
                ow = Settings(
                    **{**settings.__dict__, "overwrite": True, "skip_existing": False}
                )
                result = download_item(
                    url, str(folder), ow, media="video", index=index
                )
            if result.ok and result.path:
                print(f"[{index:04d}] OK {os.path.basename(result.path)}")
            else:
                err = result.error or "unknown"
                if is_rate_limited(err):
                    wait = compute_backoff_seconds(2, base=3.0, factor=2.0, maximum=60.0)
                    print(f"[{index:04d}] 429 sleep {wait:.1f}s")
                    time.sleep(wait)
                    result = download_item(
                        url, str(folder), settings, media="video", index=index
                    )
                    if result.ok and result.path:
                        print(f"[{index:04d}] OK retry {os.path.basename(result.path)}")
                        continue
                    err = result.error or err
                print(f"[{index:04d}] FAIL {url} :: {err}")

    left = _iter_mismatched(folder)
    print(f"remaining mismatches: {len(left)}")
    return 1 if left else 0


if __name__ == "__main__":
    raise SystemExit(main())
