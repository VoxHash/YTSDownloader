# Getting Started

## Prerequisites

- Python 3.10+ (validated with Python 3.14)
- `ffmpeg` available on `PATH`
- Optional: Node.js for yt-dlp JavaScript extraction (`JS_RUNTIME=node`)
- Optional: browser cookies when platforms require authentication

## Setup

```bash
git clone https://github.com/VoxHash/YTSDownloader.git
cd YTSDownloader
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\activate`.

## Configure

Edit `config.ini` as needed:

| Key | Purpose |
| --- | --- |
| `THEME` | Theme folder under `themes/` (default `DarkFreeze`) |
| `COOKIES_FROM_BROWSER` | Browser name for cookies (`chrome`, `firefox`, …) |
| `COOKIES_FILE` | Path to an exported cookies file |
| `JS_RUNTIME` | Runtime name (default `node`) |
| `JS_RUNTIME_PATH` | Absolute path to the runtime binary (optional if on `PATH`) |

No API keys or cloud secrets are required.

## First Run

```bash
python main.py
```

1. Choose an output folder.
2. Paste a platform URL.
3. Optionally select a PNG watermark.
4. Click **Start Download**.

If YouTube returns a bot-check / sign-in error, configure cookies in `config.ini` and retry. See [troubleshooting.md](troubleshooting.md).
