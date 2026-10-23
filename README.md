# YTSDownloader

> Multi-platform download suite for video/audio from YouTube, Instagram, Facebook, TikTok, and related hosts — with a concurrent queue, link grabber, optional watermarking, and a local metadata bridge for music-session matching. Built with PyQt6.

[![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)](https://github.com/VoxHash/YTSDownloader/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org/)
[![PyQt6](https://img.shields.io/badge/pyqt6-6.10+-blue.svg)](https://pypi.org/project/PyQt6/)

## Features

- **Suite UI**: Sidebar navigation — Download, Queue, Link Grabber, Metadata Bridge, Settings
- **URL drop zone**: Drag links (or a text file of URLs) onto Download
- **Queue filters**: Filter by state and search title / URL / message
- **Multi-platform**: YouTube (channels / videos / Shorts / playlists), Instagram, Facebook, TikTok
- **Concurrent queue**: Worker limit, retries, playlist start-slot pacing, rate-limit backoff
- **Queue persistence**: Local JSON under `.ytsdownloader/` survives restarts (pending items stay paused until Start)
- **Export presets**: Audio only, Video + audio, Watermark (and Custom); apply on enqueue or batch to selected / queued items
- **Link grabber**: Paste many URLs; resolve and enqueue in batch
- **Metadata bridge**: Read the open desktop music session (MPRIS on Linux) → search-match → audio download
- **Watermarking**: Optional PNG overlay via moviepy + ffmpeg
- **Auth helpers**: Browser cookies or cookie file (`COOKIES_FROM_BROWSER=brave:Default` supported)
- **Legacy UI**: `python main.py --legacy` for the classic tabs

## Quick Start

### Prerequisites

- Python 3.10+
- ffmpeg on `PATH`
- Optional: Node.js (`node`) for yt-dlp JS runtime
- Optional: browser cookies when platforms require authentication
- Optional (Linux metadata bridge): `dbus-send` or `busctl`

### Install and run

```bash
git clone https://github.com/VoxHash/YTSDownloader.git
cd YTSDownloader
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
# or: ./run.sh
```

Prefer the `.venv/bin/...` paths — they work in **bash**, **zsh**, and **fish** without activating. If you want a activated shell:

- bash/zsh: `source .venv/bin/activate`
- fish: `source .venv/bin/activate.fish`
- Windows: `.venv\Scripts\activate`

Do not run `source .venv/bin/activate` in fish (that script is bash-only and fails with `case` errors).

### Configuration

Edit in **Settings** (Save to `config.ini`) or edit the file directly:

| Setting | Description | Default |
| --- | --- | --- |
| `THEME` | Theme folder under `themes/` | `SuiteDark` |
| `COUNT_TIMER_ONGOING` | Seconds between playlist/job *starts* | `2.5` |
| `COOKIES_FROM_BROWSER` | Browser cookie source | empty |
| `COOKIES_FILE` | Cookie file path | empty |
| `JS_RUNTIME` | JS runtime name | `node` |
| `JS_RUNTIME_PATH` | Absolute runtime path | empty |
| `MAX_WORKERS` | Concurrent download workers | `2` |
| `MAX_RETRIES` | Retries per item | `3` |
| `BACKOFF_BASE` | Exponential retry backoff base (seconds) | `2` |
| `BACKOFF_FACTOR` | Backoff multiplier per retry | `2` |
| `BACKOFF_MAX` | Cap on retry wait (seconds) | `90` |
| `AUDIO_FORMAT` | Audio extract format | `m4a` |
| `VIDEO_FORMAT` | yt-dlp format expression | `bestvideo+bestaudio/best` |
| `DEFAULT_OUTPUT` | Default output folder | empty |

No cloud API keys are required. Treat cookie files as secrets.

## Usage

1. Launch `.venv/bin/python main.py` (or `./run.sh`)
2. On **Download**, pick an **Export preset**, set output folder, paste or drop a URL → **Resolve & Queue** → **Start Queue**
3. Or use **Link Grabber** for many URLs (uses the Download page preset)
4. Or use **Metadata Bridge** with a playing desktop music session / catalog URL
5. Monitor **Queue** (filter by state / search); optionally **Apply to selected** / **Apply to queued** with another preset

Full guides: [docs/getting-started.md](docs/getting-started.md) · [docs/usage.md](docs/usage.md) · [docs/architecture.md](docs/architecture.md)

## Examples

- [Single YouTube video](docs/examples/example-01.md)
- [Watermarked export](docs/examples/example-02.md)

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Support / Security

- Support: [SUPPORT.md](SUPPORT.md) · contact@voxhash.dev
- Security: [SECURITY.md](SECURITY.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)

## License

MIT — see [LICENSE](LICENSE).

Maintained by **VoxHash Technologies**.
