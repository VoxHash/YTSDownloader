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
| `parse_companion_payload` / `consume_companion_inbox` | Browser companion local inbox (URLs only; desktop downloads; optional Go/Ruby helpers) |
| `normalize_urls` / `normalize_paths` | Batch URL/path normalize (optional Rust `yts-normalize`) |
| `apply_process_priority` | Optional nice / idle I/O (optional C/`zig cc` `yts-prio`) |
| `native_status` / `find_binary` / `native_bin_candidates` | Discover optional sidecars (`YTS_NATIVE_DIR`, freeze `<onedir>/native/bin`, checkout, cwd) |
| `resolve_url` / `resolve_many` | Expand playlist / channel / profile URLs (shallow) |
| `crawl_profile` / `crawl_many` / `CrawlMode` | Cookie-gated profile crawl (shallow / deep / videos / shorts / posts) with limit + pacing; adult-tube multi-tab + GIF/album harvest; `rule34_video` listing pagination |
| `ytscore.adult_tube` helpers | Profile tabs, HTML listing harvest, GIF/photo CDN rewrite |
| `ytscore.rule34_video` helpers | Host detect, listing harvest, CDN rewrite + direct stream download |
| `DownloadQueue` | Concurrent workers with start-slot pacing, retries, `retry_jobs` / `retry_failed`, `remove_jobs` / `clear_all` / `force_download` |
| `get_existing_directory` / `volume_sidebar_paths` | Output-folder picker with Linux sidebar URLs (system root + mounts) |
| `resolve_app_icon_path` (`ytscore.icons`) | Locate Suite app icon under `assets/icons/` |
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
