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

1. **Configuration** — `config.ini` selects theme, playlist pacing, backoff, cookies, JS runtime, worker/retry limits, and formats. Suite Settings can write the same keys back atomically (`save_settings`).
2. **UI (Suite)** — Sidebar navigation: Download (with URL drop zone), Queue (state/search filters, failure triage + one-click retry), Link Grabber, Metadata Bridge, editable Settings. Dark suite theme under `themes/SuiteDark/`.
3. **UI (Legacy)** — `python main.py --legacy` keeps the classic multi-tab window.
4. **Extraction** — yt-dlp resolves playlists/profiles and downloads best video+audio or audio-only.
5. **Queue** — Thread-pool workers with start-slot pacing, exponential retry backoff (harder on HTTP 429), and per-item progress. Snapshot persistence via `ytscore.persist` writes `.ytsdownloader/queue_state.json`; restore remaps in-flight jobs to queued (no auto-start). Export presets (`ytscore.presets`) set per-job media / watermark / container on enqueue or batch-apply. Failure triage (`ytscore.triage`) classifies errors; `retry_jobs` / `retry_failed` re-queue cleanly without dropping URL or export options.
6. **Metadata bridge** — Reads the open desktop music-session metadata (MPRIS on Linux), builds a search query, and queues a matching public-host audio download.
7. **Post-process** — Optional full-frame PNG watermark composite (Watermark export preset or Custom with a PNG path).
8. **Diagnostics** — Logging panels and metadata cache hit/miss counters.

## Runtime dependencies

- **Python packages**: yt-dlp, PyQt6, moviepy, Pillow, numpy
- **System**: ffmpeg (mux/encode), optional Node.js for extractor JS challenges
- **Optional**: session bus tools (`dbus-send` / `busctl`) for the metadata bridge on Linux
