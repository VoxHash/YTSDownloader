# CLI Notes

`YTSDownloader` ships as a GUI application (`python main.py`). There is no first-party CLI subcommand surface yet.

## Related commands used during setup and validation

```bash
# Install
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Syntax check
python -m py_compile main.py

# Launch GUI
python main.py

# System dependency checks
ffmpeg -version
node -v

# Optional direct extractor probe (same backend as the app)
yt-dlp --js-runtimes node --cookies-from-browser chrome -F "https://www.youtube.com/watch?v=VIDEO_ID"
```

Roadmap items for a future dedicated CLI are tracked in [ROADMAP.md](../ROADMAP.md).
