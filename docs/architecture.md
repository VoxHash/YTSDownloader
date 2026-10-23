# Architecture

```text
config.ini
    │
    ▼
main.py ──► ytsgui (Suite UI)          [--legacy ► classic tabs]
                │
                ▼
            ytscore
                ├─ settings / auth opts
                ├─ resolvers (playlist / channel / profile)
                ├─ download queue (workers, retries, progress)
                ├─ downloader (yt-dlp video / audio)
                ├─ metadata bridge (local MPRIS session → search match)
                └─ watermark (moviepy + Pillow + ffmpeg)
```

## Language choice

Downloads are network-bound. The suite stays on **Python + PyQt6 + yt-dlp** so extractor maintenance stays with yt-dlp and the GUI remains one process. A Rust/Go rewrite is deferred unless profiling shows a clear CPU bottleneck (unlikely for typical I/O-heavy downloads).

## Layers

1. **Configuration** — `config.ini` selects theme, pacing, cookies, JS runtime, worker/retry limits, and formats.
2. **UI (Suite)** — Sidebar navigation: Download, Queue, Link Grabber, Metadata Bridge, Settings. Dark suite theme under `themes/SuiteDark/`.
3. **UI (Legacy)** — `python main.py --legacy` keeps the classic multi-tab window.
4. **Extraction** — yt-dlp resolves playlists/profiles and downloads best video+audio or audio-only.
5. **Queue** — Thread-pool workers with per-item progress, retries, and pacing.
6. **Metadata bridge** — Reads the open desktop music-session metadata (MPRIS on Linux), builds a search query, and queues a matching public-host audio download.
7. **Post-process** — Optional full-frame PNG watermark composite.
8. **Diagnostics** — Logging panels and metadata cache hit/miss counters.

## Runtime dependencies

- **Python packages**: yt-dlp, PyQt6, moviepy, Pillow, numpy
- **System**: ffmpeg (mux/encode), optional Node.js for extractor JS challenges
- **Optional**: session bus tools (`dbus-send` / `busctl`) for the metadata bridge on Linux
