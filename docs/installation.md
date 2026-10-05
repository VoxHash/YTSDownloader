# Installation

## System packages

### Debian / Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-venv ffmpeg
# optional JS runtime
sudo apt install -y nodejs
```

### Fedora

```bash
sudo dnf install -y python3 ffmpeg nodejs
```

### macOS (Homebrew)

```bash
brew install python ffmpeg node
```

### Windows

1. Install Python 3.10+ from https://www.python.org/downloads/
2. Install FFmpeg and add it to `PATH` (https://ffmpeg.org/download.html)
3. Optional: install Node.js from https://nodejs.org/

## Python dependencies

```bash
cd YTSDownloader
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Pinned packages (from `requirements.txt`):

- `yt-dlp==2026.3.3`
- `numpy==2.4.3`
- `moviepy==2.2.1`
- `pillow==11.3.0`
- `PyQt6==6.10.2`

## Verify

```bash
python -m py_compile main.py
ffmpeg -version
python -c "import yt_dlp, moviepy, PyQt6; print('ok')"
```
