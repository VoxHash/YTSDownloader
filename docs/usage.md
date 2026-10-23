# Usage

## Launch

```bash
.venv/bin/python main.py
# or: ./run.sh
```

Classic tabbed UI:

```bash
.venv/bin/python main.py --legacy
```

Optional activation: bash/zsh `source .venv/bin/activate`, fish `source .venv/bin/activate.fish`.

## Suite flow

1. Open **Download**, set an output folder, paste a URL, or drop links onto the drop zone (a single URL fills the field; multiple URLs crawl into the queue).
2. Choose an **Export preset** (Audio only, Video + audio, Watermark, or Custom). Presets set media / container / watermark for new jobs; Watermark requires a PNG path.
3. Optionally set **Crawl mode** and **Limit** (1–500). Shallow is a single-pass resolve. Deep / Videos / Shorts / Posts need cookie auth (`COOKIES_FROM_BROWSER` or `COOKIES_FILE`) and only enumerate content your signed-in session can already reach — no paywall or DRM bypass.
4. **Resolve & Queue**, then open **Queue** and press **Start** (or use **Start Queue** on Download).
5. Filter the queue by **State** and/or **Search** (title, URL, message, export label).
6. Optionally pick a preset on Queue and **Apply to selected** rows or **Apply to queued** items (metadata-bridge search-audio jobs are left unchanged).
7. When items fail, select a row in the **Failure triage** panel to see the classified category and full error; use **Retry selected** or **Retry failed** (preserves URL / export options; press **Start** if the queue is paused). Right-click a row for **Remove from queue** or **Force download** (starts that item immediately, skipping pace wait, even if the queue is stopped).
8. Use **Link Grabber** to paste many URLs (one per line); enqueue uses the Download page preset and crawl mode / limit.
9. Optional: a browser companion (or script) can drop URLs into `.ytsdownloader/inbox/` or append NDJSON to `.ytsdownloader/companion_inbox.jsonl` while the Suite is open — the desktop app remains the downloader (see [Architecture](architecture.md#browser-companion-handoff-contract)).
10. Use **Metadata Bridge** while a desktop music client is playing to queue a matching public-host audio download.
11. Use **Settings** to edit and **Save** `config.ini` (cookies, pace, backoff, workers, formats, status analytics); most knobs apply without restarting the app.
12. Watch per-item progress on the Queue page (Export column shows audio / video / video+wm). With **Show analytics in status bar** enabled (default), the status bar shows local session **OK** / **Err** counts plus **Last** and **Avg** job durations — nothing is sent over the network.

## Queue persistence

The Suite saves the download queue to `.ytsdownloader/queue_state.json` (gitignored) whenever items are enqueued, change state, you clear finished / clear all, or the app closes.

On the next launch the queue is restored into the table. Items that were **running** come back as **queued** with a resume hint — downloads are **not** auto-started. Press **Start** when you are ready.

**Clear Finished** removes done / failed / cancelled jobs from both the table and the saved file. **Clear All** asks for confirmation, then removes every item and persists the empty queue.

On Linux, **Browse** for the output folder (Download page and Settings default output) opens a Qt dialog whose sidebar lists the local system root (**Computer** / `/`) plus mounted volumes under `/run/media/$USER`, `/media/$USER`, and real `/mnt` mounts. Standard places such as Desktop, Documents, Downloads, and Trash are omitted.

## Platform URL patterns

- YouTube channel: `https://www.youtube.com/@channelname`
- YouTube video / Short / playlist URLs
- Instagram profile / reel / post URLs
- Facebook page / post / watch URLs
- TikTok profile / video URLs
- Catalog track / playlist / album URLs for the metadata bridge

## Auth check

Use **Check Auth** after entering a URL to validate cookie / JS runtime extraction without starting a full batch.

## Outputs

- Media files land in the selected folder
- Optional watermark PNG composites when configured
- Queue spaces playlist/job starts by `COUNT_TIMER_ONGOING` and retries failed items up to `MAX_RETRIES` with exponential backoff (`BACKOFF_*`; harder on HTTP 429)
