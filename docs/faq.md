# FAQ

## Does YTSDownloader need API keys?

No. It uses `yt-dlp` with optional local browser cookies / cookie files.

## Which Python version is required?

Python 3.10+ is recommended. Fresh validation succeeded on Python 3.14.

## Why do downloads fail on YouTube without cookies?

Many YouTube extractions requests require authenticated cookies to pass bot checks. Set `COOKIES_FROM_BROWSER` or `COOKIES_FILE`.

## Why do private / unlisted playlists fail?

Private and unlisted playlists (including adult-tube lists) only resolve when your configured browser cookies or cookie file belong to a session that can already open them. The Suite does not bypass DRM, paywalls, or other people's accounts.

## Why do some hosts return HTTP 403?

Install dependencies from `requirements.txt` (includes `curl_cffi`) and keep **TLS impersonate** set to `chrome` in Suite Settings (or `IMPERSONATE = chrome` in `config.ini`) unless you intentionally clear it to disable.

## What are crawl modes?

On **Download**, **Crawl mode** controls how profile / channel URLs expand into queue items. **Shallow** is a single-pass resolve (cookies optional). **Deep**, **Videos**, **Shorts**, and **Posts** need cookie auth and pace multi-tab or feed enumeration. They only list content your signed-in session can already reach — not private or paywalled surfaces. For adult-tube model/user profiles, Deep paces videos + uploads + GIFs + albums/photos; Shorts targets GIF/clip listings; Posts expands album listings into photo pages (clean-room HTML harvest where yt-dlp flat extract is insufficient). **Limit** caps how many items are enqueued (`1`–`10000`, or `0` / **Unlimited**).

## How do I avoid re-downloading files I already have?

Keep **Skip existing files** on (default; `SKIP_EXISTING = true`). The Suite skips when a file whose name contains `[media-id]` is already in the output folder, and uses yt-dlp’s download archive (`.yts_download_archive.txt` in that folder). Turn on **Overwrite** (`OVERWRITE = true`) only when you want a fresh copy — overwrite wins over skip. **Number files in queue** (`NUMBER_FILES`) controls whether new files get a `0001_` prefix.

## Can I run without a watermark?

Yes. Leave the watermark field empty; the downloaded file is kept/renamed without moviepy overlay.

## Is there a headless CLI?

Not yet. Launch with `python main.py`. Related notes are in [cli.md](cli.md).

## How do I build a Windows / macOS / Linux distributable?

Use **PyInstaller `onedir`** on each target OS (no cross-compile). Keep **ffmpeg** and **ffprobe** on the end-user `PATH`.

- Linux / macOS: `./scripts/build_pyinstaller.sh` (optional `SMOKE=1`)
- Windows: `.\scripts\build_pyinstaller.ps1`

See [Installation → Packaging](installation.md#packaging-windows--macos--linux-distributables). A full required cross-OS freeze CI matrix is out of scope; optional Ubuntu freeze is Actions → **Freeze (manual)** only.

## Can a browser extension download for me?

No. A companion may only hand off media URLs (drop zone, Link Grabber, or the local `.ytsdownloader/` inbox). The desktop Suite always resolves and downloads. See [cross-platform.md](cross-platform.md) and [Architecture](architecture.md#browser-companion-handoff-contract).

## How do Android / Quest work with the desktop Suite?

Export inbox JSON (**Export to Downloads**) from the companion, `adb pull` into `.ytsdownloader/inbox/` while the Suite is running (poll ~1.5s). Schema v1, `source` `android-companion` or `quest-companion`. Full workflow: [cross-platform.md](cross-platform.md).

## Who maintains this?

VoxHash Technologies — contact@voxhash.dev
