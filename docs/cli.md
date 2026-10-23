# CLI Notes

`YTSDownloader` ships as a GUI application (`python main.py`). There is no first-party CLI subcommand surface yet.

## Related commands used during setup and validation

```bash
# Install (shell-agnostic; works in fish without activate)
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# Syntax check
.venv/bin/python -m py_compile main.py

# Launch GUI
.venv/bin/python main.py
# or: ./run.sh

# System dependency checks
ffmpeg -version
node -v

# Optional direct extractor probe (same backend as the app)
.venv/bin/yt-dlp --js-runtimes node --cookies-from-browser chrome -F "https://www.youtube.com/watch?v=VIDEO_ID"
```

Activation is optional: bash/zsh `source .venv/bin/activate`, fish `source .venv/bin/activate.fish`.

Roadmap items for a future dedicated CLI are tracked in [ROADMAP.md](../ROADMAP.md).
