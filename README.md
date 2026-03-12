# YTSDownloader

`YTSDownloader` is a creator-focused desktop tool for downloading short-form videos (YouTube, Instagram, Facebook, TikTok) and exporting branded outputs with watermark support.

## Features
- Bulk link extraction from profile/channel URLs
- GUI workflow built with PyQt6
- Watermark merge pipeline using moviepy
- `yt-dlp` authentication support via browser cookies or cookie file
- Theme support through `themes/`

## Installation
1. Clone the repository:
```bash
git clone https://github.com/VoxHash-Technologies/YTSDownloader.git
cd YTSDownloader
```
2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Install system dependency:
- `ffmpeg` must be available in your `PATH`

## Usage
1. Update `config.ini` as needed (theme, cookies, JavaScript runtime).
2. Start the app:
```bash
./.venv/bin/python main.py
```
3. In the GUI, provide:
- output folder
- source profile/channel URL
- optional watermark image

Additional guides are in `docs/`.

## Contributing
Read `CONTRIBUTING.md` for development setup, validation steps, and pull request requirements.

## Project Docs
- `CHANGELOG.md`
- `ROADMAP.md`
- `DEVELOPMENT_GOALS.md`
- `docs/index.md`
