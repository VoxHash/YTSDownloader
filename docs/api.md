# API Surface

`YTSDownloader` does not expose an HTTP API. The callable surface is the Python module in `main.py`.

## Notable helpers

| Symbol | Role |
| --- | --- |
| `read_config(path)` | Load `config.ini` |
| `with_auth_opts(ydl_opts)` | Attach cookies / JS runtime options for yt-dlp |
| `get_video_links(url)` | Resolve YouTube channel/video URLs to a link list |
| `get_instagram_links(url)` | Resolve Instagram URLs |
| `get_facebook_links(url)` | Resolve Facebook URLs |
| `get_tiktok_links(url)` | Resolve TikTok URLs |
| `save_original_names(links, output_path, output_format)` | Write `original_names.txt` |
| `add_watermark(video_path, watermark_path, output_path)` | Overlay PNG watermark via moviepy |
| `WorkerThread` | Background download + optional watermark worker |
| `MainWindow` | PyQt6 application window |

These helpers are intended for the GUI workflow. Importing them for scripts is possible but unsupported as a stable public API.
