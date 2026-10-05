# Usage

## Launch

```bash
source .venv/bin/activate
python main.py
```

## Basic flow

1. Open the tab for YouTube, Instagram, Facebook, or TikTok.
2. Choose an output folder.
3. Paste a channel/profile URL or a direct video URL.
4. Optionally browse to a PNG watermark.
5. Select WebM or MP4.
6. Click **Start Download** and watch the progress bar / logs.

## Platform URL patterns

- YouTube channel: `https://www.youtube.com/@channelname`
- YouTube video / Short: `https://www.youtube.com/watch?v=…` or `/shorts/…`
- Instagram profile / reel / post URLs
- Facebook page / post / watch URLs
- TikTok profile / video URLs

## Auth check

Use **Check Auth** on a tab after entering a URL to validate cookie / JS runtime extraction without starting a full batch.

## Outputs

- Media files land in the selected folder
- `original_names.txt` maps source URLs to sanitized titles
