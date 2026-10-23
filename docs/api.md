# API Surface

`YTSDownloader` does not expose an HTTP API. Prefer the Suite packages (`ytscore`, `ytsgui`); legacy helpers remain in `main.py`.

## Suite (`ytscore`)

| Symbol | Role |
| --- | --- |
| `load_settings` / `save_settings` / `Settings` | Load/save `config.ini` (pace, backoff, workers, cookies, status analytics) |
| `apply_auth_opts` | Attach cookies / JS runtime options for yt-dlp |
| `SessionAnalytics` / `format_duration` | Local session success / error / timing counters (no network) |
| `compute_backoff_seconds` / `is_rate_limited` | Retry delay and rate-limit detection |
| `classify_failure` / `failure_detail_text` | Coarse failure categories for Queue triage |
| `parse_companion_payload` / `consume_companion_inbox` | Browser companion local inbox (URLs only; desktop downloads) |
| `resolve_url` / `resolve_many` | Expand playlist / channel / profile URLs |
| `DownloadQueue` | Concurrent workers with start-slot pacing, retries, and `retry_jobs` / `retry_failed` |
| `download_item` | Single URL download with exponential backoff retries |
| `SuiteWindow` (`ytsgui`) | Suite sidebar UI |

## Legacy (`main.py`)

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
| `MainWindow` | Classic PyQt6 window (`python main.py --legacy`) |

These helpers are intended for the GUI workflow. Importing them for scripts is possible but unsupported as a stable public API.
