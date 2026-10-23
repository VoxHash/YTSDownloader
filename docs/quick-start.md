# Quick Start

End-to-end path that matches a fresh clone:

```bash
git clone https://github.com/VoxHash/YTSDownloader.git
cd YTSDownloader
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
ffmpeg -version
.venv/bin/python -m py_compile main.py
.venv/bin/python main.py
# or: ./run.sh
```

Shell-agnostic tip: use `.venv/bin/python` / `.venv/bin/pip` (or `./run.sh`) so you never need `activate`. In fish, if you do activate, use `source .venv/bin/activate.fish` — not the bash `activate` script.

Then in the GUI:

1. Browse to an empty output folder.
2. Enter a public video URL on the YouTube tab.
3. Leave watermark empty for a plain download, or pick a PNG.
4. Choose WebM or MP4 and start the job.

If extraction fails with a bot / login message, set `COOKIES_FROM_BROWSER` or `COOKIES_FILE` in `config.ini` and restart the app.
