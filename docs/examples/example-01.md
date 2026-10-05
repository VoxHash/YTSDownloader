# Example 01: Single YouTube video

Download one public YouTube video without a watermark.

## Steps

1. Install and launch:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

2. Open the **YouTube Downloader** tab.
3. Browse to an output folder such as `~/Videos/yts-out`.
4. Paste a video URL, for example `https://www.youtube.com/watch?v=VIDEO_ID`.
5. Leave watermark empty, choose **MP4**, click **Start Download**.

## Expected result

- A numbered media file appears in the output folder
- `original_names.txt` lists `URL|title.mp4`

## If extraction fails

Set cookies in `config.ini` and restart:

```ini
COOKIES_FROM_BROWSER = firefox
```
