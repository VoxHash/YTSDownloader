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
                ├─ analytics (local session counters)
                ├─ resolvers (playlist / channel / profile)
                ├─ download queue (workers, retries, progress)
                ├─ downloader (yt-dlp video / audio)
                ├─ companion inbox (browser → desktop URL handoff)
                ├─ metadata bridge (local MPRIS session → search match)
                └─ watermark (moviepy + Pillow + ffmpeg)
```

## Language choice

Downloads are network-bound. The suite stays on **Python + PyQt6 + yt-dlp** so extractor maintenance stays with yt-dlp and the GUI remains one process. A Rust/Go rewrite is deferred unless profiling shows a clear CPU bottleneck (unlikely for typical I/O-heavy downloads).

### ffmpeg / moviepy profiling (v0.3.3 gate)

Conditional milestone: add focused hot-path helpers **only if** ffmpeg **process spawn** is a meaningful share of wall time on realistic Suite jobs — keep Python orchestration either way.

Local measurements (`.venv/bin/python`, system ffmpeg, Suite `ytscore.watermark.add_watermark`, repo `watermark.png`):

| Workload | Wall (approx.) | Notes |
| --- | --- | --- |
| `ffmpeg -version` spawn | ~33 ms mean | Process start baseline |
| Direct single-ffmpeg overlay (2s / 15s synth) | ~0.11 s / ~0.45 s | One filtergraph encode |
| moviepy watermark (2s / 15s synth) | ~0.26 s / ~2.9 s | ~6–8 imageio-ffmpeg Popens; spawn estimate ≪ encode time on 15s |
| Live short-URL download attempt | ~20 s | Extract/auth retries; no watermark reached |

**Result:** spawn is not the bottleneck; network/extract and (when watermarking) re-encode dominate. No native helpers or process-reuse shipped. moviepy remains slower than a single ffmpeg filtergraph because it re-encodes frame-by-frame — that is encode cost, not spawn cost.

**Revisit when:** watermark-only batches of long local files become the primary workload and fresh profiles show process start (not libx264 / Python frames) dominating samples, or redundant per-job ffmpeg probes multiply well beyond a handful of spawns.

## Layers

1. **Configuration** — `config.ini` selects theme, playlist pacing, backoff, cookies, JS runtime, worker/retry limits, formats, and optional status analytics. Suite Settings can write the same keys back atomically (`save_settings`).
2. **UI (Suite)** — Sidebar navigation: Download (with URL drop zone, crawl mode + limit), Queue (state/search filters, failure triage + one-click retry), Link Grabber, Metadata Bridge, editable Settings. Dark suite theme under `themes/SuiteDark/`. Optional permanent status-bar analytics (OK / Err / Last / Avg).
3. **UI (Legacy)** — `python main.py --legacy` keeps the classic multi-tab window.
4. **Extraction** — yt-dlp resolves playlists/profiles and downloads best video+audio or audio-only. `ytscore.crawl` adds deeper profile/channel modes (multi-tab YouTube; flat social feeds) gated on cookie auth; pacing between tab fetches reuses `COUNT_TIMER_ONGOING` / backoff helpers. Only legally reachable surfaces for the signed-in session.
5. **Queue** — Thread-pool workers with start-slot pacing, exponential retry backoff (harder on HTTP 429), and per-item progress. Snapshot persistence via `ytscore.persist` writes `.ytsdownloader/queue_state.json`; restore remaps in-flight jobs to queued (no auto-start). Export presets (`ytscore.presets`) set per-job media / watermark / container on enqueue or batch-apply. Failure triage (`ytscore.triage`) classifies errors; `retry_jobs` / `retry_failed` re-queue cleanly without dropping URL or export options. Context actions call `remove_jobs` / `force_download` (front-of-queue + pace bypass); folder Browse uses `ytscore.folder_dialog` sidebar URLs for external volumes.
6. **Companion handoff** — Optional browser companion (or script) may send media URLs into a local inbox under `.ytsdownloader/`; the Suite polls and feeds the same resolve/queue path as drag-and-drop. The desktop app remains the only downloader.
7. **Metadata bridge** — Reads the open desktop music-session metadata (MPRIS on Linux), builds a search query, and queues a matching public-host audio download.
8. **Post-process** — Optional full-frame PNG watermark composite (Watermark export preset or Custom with a PNG path).
9. **Diagnostics** — Logging panels, metadata cache hit/miss counters, and local session analytics (`ytscore.analytics`; no network telemetry).

## Browser companion handoff contract

**Principle:** a future browser extension (or any local helper) discovers / copies media page URLs; **YTSDownloader on the desktop always performs resolve + download**. Companions must not stream media bytes into this tree.

### Current handoff channels (no extension required)

| Channel | How | Suite behavior |
| --- | --- | --- |
| Download drop zone | Drag browser links or a `.txt` / `.url` file onto Download | One URL fills the field; many URLs resolve and enqueue with the active export preset |
| Link Grabber | Paste many URLs (one per line) → enqueue | Uses the Download page preset |
| Companion inbox (local files) | Write payloads under `.ytsdownloader/` while Suite is running | Polled ~1.5s; consumed URLs take the same path as a drop |

### Local inbox protocol (v1)

Working directory is the Suite process cwd (same place as `config.ini` / `.ytsdownloader/queue_state.json`).

| Path | Role |
| --- | --- |
| `.ytsdownloader/inbox/` | Drop directory. Write a complete file (`*.txt`, `*.url`, `*.json`, `*.jsonl`, `*.urls`). After a successful read the Suite renames it to `*.processed`. |
| `.ytsdownloader/companion_inbox.jsonl` | Append-friendly NDJSON. Each line is one JSON object (or a bare URL). Suite truncates the file after consuming non-empty content. |

**Payload shapes** (parsed by `ytscore.companion.parse_companion_payload`):

```json
{"schema": 1, "url": "https://example.com/watch?v=…", "title": "optional", "source": "browser-companion", "page_url": "https://…"}
```

```json
{"urls": ["https://a.example/1", {"url": "https://a.example/2", "title": "Two"}]}
```

```text
https://example.com/one
https://example.com/two
```

Rules:

1. Only `http` / `https` URLs are accepted (`extract_urls` rules).
2. Duplicate URLs in one consume pass are collapsed.
3. Optional fields (`title`, `source`, `page_url`) are metadata for logs / future UI; download still goes through yt-dlp resolve on the desktop.
4. Companions should write complete lines/files (atomic rename into `inbox/` is preferred for large batches).
5. No localhost HTTP server and no cloud relay in v1 — file drop only, so the contract stays fish-safe and offline.

### Extension author checklist

1. Detect media page URL in the browser tab (or selected link).
2. Append one NDJSON line to `companion_inbox.jsonl` **or** write a new file under `inbox/`.
3. Leave download, cookies, pacing, retries, and export presets to the running Suite.
4. Do not ship extractor / downloader logic inside the extension for this product path.

## Runtime dependencies

- **Python packages**: yt-dlp, PyQt6, moviepy, Pillow, numpy
- **System**: ffmpeg + ffprobe (mux/encode / probe), optional Node.js for extractor JS challenges
- **Optional**: session bus tools (`dbus-send` / `busctl`) for the metadata bridge on Linux
- **Distributables**: freeze with PyInstaller `onedir` per OS; ffmpeg/ffprobe remain external — see [Installation → Packaging](installation.md#packaging-windows--macos--linux-distributables)
