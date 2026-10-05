# YTSDownloader

> Desktop tool for downloading short-form videos from YouTube, Instagram, Facebook, and TikTok with optional PNG watermarking. Built with PyQt6 for creators who need bulk downloads and brand protection.

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/VoxHash/YTSDownloader/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org/)
[![PyQt6](https://img.shields.io/badge/pyqt6-6.10+-blue.svg)](https://pypi.org/project/PyQt6/)

## Features

- **Multi-platform**: YouTube (channels / videos / Shorts), Instagram, Facebook, TikTok
- **Bulk download**: Resolve profiles/channels and download multiple items
- **Watermarking**: Optional PNG overlay via moviepy + ffmpeg
- **Auth helpers**: Browser cookies or cookie file for platforms that require login
- **JS runtime support**: Node.js integration for yt-dlp extraction challenges
- **Themed PyQt6 GUI**: Progress, logs, and per-tab workflows

## Quick Start

### Prerequisites

- Python 3.10+
- ffmpeg on `PATH`
- Optional: Node.js (`node`) for yt-dlp JS runtime
- Optional: browser cookies when YouTube/Instagram require authentication

### Install and run

```bash
git clone https://github.com/VoxHash/YTSDownloader.git
cd YTSDownloader
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Configuration

Edit `config.ini`:

| Setting | Description | Default |
| --- | --- | --- |
| `THEME` | Theme folder under `themes/` | `DarkFreeze` |
| `COUNT_TIMER_ONGOING` | Seconds between downloads | `2` |
| `COOKIES_FROM_BROWSER` | Browser cookie source | empty |
| `COOKIES_FILE` | Cookie file path | empty |
| `JS_RUNTIME` | JS runtime name | `node` |
| `JS_RUNTIME_PATH` | Absolute runtime path | empty |

No cloud API keys are required. Treat cookie files as secrets.

## Usage

1. Launch `python main.py`
2. Pick a platform tab and output folder
3. Paste a channel/profile or direct video URL
4. Optionally select a PNG watermark and choose WebM/MP4
5. Start download and monitor progress / logs

Full guides: [docs/getting-started.md](docs/getting-started.md) · [docs/usage.md](docs/usage.md)

## Examples

- [Single YouTube video](docs/examples/example-01.md)
- [Watermarked export](docs/examples/example-02.md)

## Roadmap

See [ROADMAP.md](ROADMAP.md) for near-term reliability work and creator workflow improvements.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Support / Security

- Support: [SUPPORT.md](SUPPORT.md) · contact@voxhash.dev
- Security: [SECURITY.md](SECURITY.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)

## License

MIT — see [LICENSE](LICENSE).

Maintained by **VoxHash Technologies**.
