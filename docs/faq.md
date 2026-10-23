# FAQ

## Does YTSDownloader need API keys?

No. It uses `yt-dlp` with optional local browser cookies / cookie files.

## Which Python version is required?

Python 3.10+ is recommended. Fresh validation succeeded on Python 3.14.

## Why do downloads fail on YouTube without cookies?

Many YouTube extractions requests require authenticated cookies to pass bot checks. Set `COOKIES_FROM_BROWSER` or `COOKIES_FILE`.

## What are crawl modes?

On **Download**, **Crawl mode** controls how profile / channel URLs expand into queue items. **Shallow** is a single-pass resolve (cookies optional). **Deep**, **Videos**, **Shorts**, and **Posts** need cookie auth and pace multi-tab or feed enumeration. They only list content your signed-in session can already reach via yt-dlp — not private or paywalled surfaces.

## Can I run without a watermark?

Yes. Leave the watermark field empty; the downloaded file is kept/renamed without moviepy overlay.

## Is there a headless CLI?

Not yet. Launch with `python main.py`. Related notes are in [cli.md](cli.md).

## How do I build a Windows / macOS / Linux distributable?

Use **PyInstaller `onedir`** on each target OS (no cross-compile). Keep **ffmpeg** and **ffprobe** on the end-user `PATH`. See [Installation → Packaging](installation.md#packaging-windows--macos--linux-distributables) and `./scripts/build_pyinstaller.sh`.

## Can a browser extension download for me?

No. A companion may only hand off media URLs (drop zone, Link Grabber, or the local `.ytsdownloader/` inbox). The desktop Suite always resolves and downloads. See [Architecture](architecture.md#browser-companion-handoff-contract).

## Who maintains this?

VoxHash Technologies — contact@voxhash.dev
