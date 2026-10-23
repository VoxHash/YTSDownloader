# Getting Started

## Prerequisites

- Python 3.10+ (validated with Python 3.14)
- `ffmpeg` and `ffprobe` available on `PATH`
- Optional: Node.js for yt-dlp JavaScript extraction (`JS_RUNTIME=node`)
- Optional: browser cookies when platforms require authentication
- Optional: frozen builds — see [Installation → Packaging](installation.md#packaging-windows--macos--linux-distributables)

## Setup

```bash
git clone https://github.com/VoxHash/YTSDownloader.git
cd YTSDownloader
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

Prefer `.venv/bin/python` and `.venv/bin/pip` (works in bash, zsh, and fish). Optional activation:

- bash/zsh: `source .venv/bin/activate`
- fish: `source .venv/bin/activate.fish`
- Windows: `.venv\Scripts\activate`

## Configure

Edit `config.ini` as needed:

| Key | Purpose |
| --- | --- |
| `THEME` | Theme folder under `themes/` (default `SuiteDark`) |
| `COOKIES_FROM_BROWSER` | Browser name for cookies (`chrome`, `firefox`, …) |
| `COOKIES_FILE` | Path to an exported cookies file |
| `JS_RUNTIME` | Runtime name (default `node`) |
| `JS_RUNTIME_PATH` | Absolute path to the runtime binary (optional if on `PATH`) |
| `MAX_WORKERS` | Concurrent download workers |
| `MAX_RETRIES` | Retries per queue item |
| `COUNT_TIMER_ONGOING` | Seconds between playlist/job starts (default `2.5`) |
| `BACKOFF_BASE` / `BACKOFF_FACTOR` / `BACKOFF_MAX` | Exponential retry backoff (harder on rate limits) |

No API keys or cloud secrets are required.

## First Run

```bash
.venv/bin/python main.py
# or: ./run.sh
```

1. Choose an output folder.
2. Paste a platform URL.
3. Optionally select a PNG watermark.
4. Click **Start Download**.

If YouTube returns a bot-check / sign-in error, configure cookies in `config.ini` and retry. See [troubleshooting.md](troubleshooting.md).
