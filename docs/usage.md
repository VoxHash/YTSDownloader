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

1. Open **Download**, set an output folder, paste a URL, or drop links onto the drop zone (a single URL fills the field; multiple URLs resolve into the queue).
2. Choose an **Export preset** (Audio only, Video + audio, Watermark, or Custom). Presets set media / container / watermark for new jobs; Watermark requires a PNG path.
3. **Resolve & Queue**, then open **Queue** and press **Start** (or use **Start Queue** on Download).
4. Filter the queue by **State** and/or **Search** (title, URL, message, export label).
5. Optionally pick a preset on Queue and **Apply to selected** rows or **Apply to queued** items (metadata-bridge search-audio jobs are left unchanged).
6. When items fail, select a row in the **Failure triage** panel to see the classified category and full error; use **Retry selected** or **Retry failed** (preserves URL / export options; press **Start** if the queue is paused).
7. Use **Link Grabber** to paste many URLs (one per line); enqueue uses the Download page preset.
8. Optional: a browser companion (or script) can drop URLs into `.ytsdownloader/inbox/` or append NDJSON to `.ytsdownloader/companion_inbox.jsonl` while the Suite is open — the desktop app remains the downloader (see [Architecture](architecture.md#browser-companion-handoff-contract)).
9. Use **Metadata Bridge** while a desktop music client is playing to queue a matching public-host audio download.
10. Use **Settings** to edit and **Save** `config.ini` (cookies, pace, backoff, workers, formats); most knobs apply without restarting the app.
11. Watch per-item progress on the Queue page (Export column shows audio / video / video+wm).

## Queue persistence

The Suite saves the download queue to `.ytsdownloader/queue_state.json` (gitignored) whenever items are enqueued, change state, you clear finished jobs, or the app closes.

On the next launch the queue is restored into the table. Items that were **running** come back as **queued** with a resume hint — downloads are **not** auto-started. Press **Start** when you are ready.

**Clear Finished** removes done / failed / cancelled jobs from both the table and the saved file.

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
