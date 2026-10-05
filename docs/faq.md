# FAQ

## Does YTSDownloader need API keys?

No. It uses `yt-dlp` with optional local browser cookies / cookie files.

## Which Python version is required?

Python 3.10+ is recommended. Fresh validation succeeded on Python 3.14.

## Why do downloads fail on YouTube without cookies?

Many YouTube extractions requests require authenticated cookies to pass bot checks. Set `COOKIES_FROM_BROWSER` or `COOKIES_FILE`.

## Can I run without a watermark?

Yes. Leave the watermark field empty; the downloaded file is kept/renamed without moviepy overlay.

## Is there a headless CLI?

Not yet. Launch with `python main.py`. Related notes are in [cli.md](cli.md).

## Who maintains this?

VoxHash Technologies — contact@voxhash.dev
