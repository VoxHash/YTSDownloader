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
2. Choose Video or Audio, then **Resolve & Queue**.
3. Open **Queue** and press **Start** (or use **Start Queue** on Download).
4. Filter the queue by **State** and/or **Search** (title, URL, message).
5. Use **Link Grabber** to paste many URLs (one per line).
6. Use **Metadata Bridge** while a desktop music client is playing to queue a matching public-host audio download.
7. Use **Settings** to edit and **Save** `config.ini` (cookies, pace, backoff, workers, formats); most knobs apply without restarting the app.
8. Watch per-item progress on the Queue page.

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
