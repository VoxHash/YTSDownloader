# Architecture

```text
config.ini ──► main.py (PyQt6 GUI)
                  │
                  ├─ link resolvers (yt-dlp extract_flat)
                  ├─ WorkerThread (download + rename)
                  └─ add_watermark (moviepy + Pillow + ffmpeg)
```

## Layers

1. **Configuration** — `config.ini` selects theme, download pacing, cookies, and JS runtime.
2. **UI** — Frameless `MainWindow` with four `VideoDownloaderTab` instances and a custom title bar themed by `themes/<THEME>/style.qss`.
3. **Extraction** — `yt-dlp` resolves playlists/profiles and downloads best video+audio.
4. **Post-process** — Optional full-frame PNG watermark composite written as WebM or MP4.
5. **Diagnostics** — Logging handler streams messages into each tab’s log panel; metadata cache hit/miss counters are shown in the UI.

## Runtime dependencies

- **Python packages**: yt-dlp, PyQt6, moviepy, Pillow, numpy
- **System**: ffmpeg (mux/encode), optional Node.js for extractor JS challenges
