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

1. Open **Download**, set an output folder, paste a URL.
2. Choose Video or Audio, then **Resolve & Queue**.
3. Open **Queue** and press **Start** (or use **Start Queue** on Download).
4. Use **Link Grabber** to paste many URLs (one per line).
5. Use **Metadata Bridge** while a desktop music client is playing to queue a matching public-host audio download.
6. Watch per-item progress on the Queue page.

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
- Queue retries failed items up to `MAX_RETRIES`
