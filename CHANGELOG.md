# Changelog

All notable changes to `YTSDownloader` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-10-23

### Added
- **Profile / channel crawl modes** behind cookie auth (`ytscore.crawl`): Shallow, Deep (multi-tab), Videos, Shorts, and Posts — deep modes require `COOKIES_FROM_BROWSER` or `COOKIES_FILE`.
- Download Suite controls: crawl mode combo + item limit (1–500); Resolve / drop / Link Grabber use the selected mode with pacing between tab fetches and backoff on rate-limit signals.
- Auth-gate hint on Download; deep crawl enumerates only surfaces the signed-in session can already reach via existing extractors (no paywall/DRM bypass).
- Unit tests and offscreen Suite smoke for crawl helpers, auth gate, and UI wiring.

### Changed
- SemVer minor bump: first shipped item from the former **Later** wave after the v0.3.x packaging baseline.
- Roadmap: cookie-auth profile crawl completed; Next / Later empty.
- Docs: usage, API, architecture, configuration, README cover crawl modes.

## [0.3.4] - 2026-10-23

### Added
- **Packaging notes** for Windows / macOS / Linux distributables: PyInstaller `onedir` primary recipe, ffmpeg/ffprobe as external PATH deps, optional Briefcase wrap, cx_Freeze called out as alternative.
- `scripts/build_pyinstaller.sh` — fish-safe local freeze helper (no venv activate required).

### Changed
- Docs kit: installation, getting-started, architecture, FAQ, troubleshooting, index, and README link the packaging section.
- Roadmap: packaging milestone completed; Next is empty (Later: deeper cookie-auth profile crawl).
- Architecture: ffmpeg spawn profiling on synthetic watermark paths — **no native hot-path helpers**; spawn is not a meaningful share of realistic Suite wall time.

### Fixed
- Parse `COUNT_TIMER_ONGOING` as float in `main.py` so the default `2.5` pacing value does not crash import (required for Suite and frozen launches).

## [0.3.3] - 2026-10-23

### Added
- Optional **local session analytics** in the Suite status bar: success count, error count, last job duration, and session average duration.
- Settings checkbox **Show analytics in status bar** (`SHOW_STATUS_ANALYTICS` in `config.ini`); default on; no network telemetry.
- `ytscore.analytics.SessionAnalytics` helpers plus unit / offscreen Suite smoke tests.

### Changed
- Settings hint documents local-only analytics; configuration / API / usage docs updated.

## [0.3.2] - 2026-10-23

### Added
- Browser **companion inbox** handoff: Suite polls `.ytsdownloader/inbox/` and `.ytsdownloader/companion_inbox.jsonl` for media URLs; desktop remains the only downloader.
- `ytscore.companion` parsers (`parse_companion_payload`, `consume_companion_inbox`) plus unit / offscreen Suite smoke tests.
- Architecture docs for the extension handoff contract (drop zone + Link Grabber + local inbox); docs index / usage / API / configuration updated.

### Changed
- Download page hint mentions the companion inbox path.

## [0.3.1] - 2026-10-23

### Added
- Queue **Failure triage** panel: select a row to see classified error category (rate limit / auth / network / unavailable / format / unknown) and full detail.
- **Retry selected** and **Retry failed** actions re-queue jobs cleanly (reset state/progress/error; preserve URL, title, media, and export options).
- `ytscore.triage` classifiers and `DownloadQueue.retry_jobs` / `retry_failed` helpers with unit / offscreen Suite smoke tests.

### Changed
- SuiteDark styles for the triage panel; Queue hint documents triage + retry.

## [0.3.0] - 2026-10-23

### Added
- Named **export presets** on Download: Audio only, Video + audio, Watermark, and Custom — choosing a preset sets media / container / watermark options for newly enqueued jobs.
- Queue **Apply to selected** / **Apply to queued** to batch-update export options on pending items; Export column shows audio / video / video+wm / search audio.
- Per-job `watermark_path` and `output_format` on the download queue (persisted in queue JSON); download pipeline prefers per-job options over queue defaults.
- `ytscore.presets` helpers and unit / offscreen Suite smoke tests.

### Changed
- SemVer minor bump: first shipped item from the former **Next** wave after the v0.2.x Settings / persistence baseline.

## [0.2.4] - 2026-10-23

### Added
- Suite **Settings** form edits the real `config.ini` keys (theme, cookies, JS runtime, workers/retries, pace, backoff, formats, default output) with atomic write via `ytscore.settings.save_settings`.
- Save applies into the running `Settings` / queue object without a full restart (pace, backoff, cookies, formats, retries); worker count takes effect on the next Start Queue.
- Unit tests for write/read round-trip and offscreen Settings UI smoke.

### Changed
- Settings page is no longer reload-only; Reload still refreshes the form from disk.

## [0.2.3] - 2026-10-23

### Added
- Local **queue persistence** to `.ytsdownloader/queue_state.json` (gitignored): saves on enqueue/state changes, Clear Finished, and app close; restores on Suite startup.
- Safer restore: in-progress (`running`) items become **queued** with a “press Start Queue to resume” message — downloads are **not** auto-restarted.

### Changed
- **Clear Finished** removes done/failed/cancelled jobs from the queue engine (and persisted state), not only from the table view.
- Queue page hint documents restore-without-auto-start behavior.

## [0.2.2] - 2026-10-23

### Added
- Shared playlist **start-slot pacing** so concurrent queue workers space job starts by `COUNT_TIMER_ONGOING`.
- Rate-limit-aware **exponential backoff** on download retries (`BACKOFF_BASE`, `BACKOFF_FACTOR`, `BACKOFF_MAX`); HTTP 429 / rate-limit errors use a harder base and extend the global queue cooldown.
- `ytscore.backoff` helpers for detection and delay calculation (unit-tested without live hosts).

### Changed
- Default playlist pace raised to **2.5s** (`COUNT_TIMER_ONGOING`).
- Suite Settings overview shows pace and backoff knobs.
- Retry waits no longer cap at a flat 8s; they follow configured exponential backoff (max 90s by default).

## [0.2.1] - 2026-10-23

### Added
- Queue page filters: state combo (All / queued / running / done / failed / cancelled) and text search over title, URL, and message.
- Download page drag-and-drop URL zone (browser links or `.txt` / `.url` files); single drop fills the URL field, multiple URLs resolve into the queue.
- `extract_urls` helper in `ytscore.util` for paste/drop parsing.

### Changed
- SuiteDark styles for the drop zone (dashed target, green highlight while dragging).

## [0.2.0] - 2026-10-23

### Added
- Modular core package (`ytscore`): settings, resolvers, concurrent download queue with retries, downloader, watermark, metadata bridge.
- Suite GUI (`ytsgui`): sidebar navigation, download page, queue table, link grabber, metadata bridge, settings overview.
- SuiteDark theme with dark hierarchy and queue-focused layout.
- Metadata bridge reads the local music desktop session (MPRIS on Linux) and queues matching public-host audio downloads.
- Config knobs: `MAX_WORKERS`, `MAX_RETRIES`, `AUDIO_FORMAT`, `VIDEO_FORMAT`, `DEFAULT_OUTPUT`.
- `python main.py --legacy` keeps the classic tabbed window.

### Changed
- Default entrypoint launches the Suite UI.
- Default theme set to `SuiteDark`.
- Architecture docs updated for the modular layout.
- Docs prefer shell-agnostic `.venv/bin/python` / `.venv/bin/pip` (and `./run.sh`); fish users should use `activate.fish`, not bash `activate`.

## [0.1.0] - 2026-10-05

### Added
- PyQt6 desktop workflow for multi-platform short-video downloading (YouTube, Instagram, Facebook, TikTok).
- Watermarking pipeline with moviepy and Pillow.
- Runtime configuration in `config.ini` for theme, cookies, and JS runtime.
- Standardized documentation kit (`README`, `CONTRIBUTING`, `ROADMAP`, `CHANGELOG`, `CODE_OF_CONDUCT`, `SECURITY`, `SUPPORT`, `docs/`).
- GitHub issue and pull request templates.

### Changed
- Cleared machine-specific `JS_RUNTIME_PATH` from the default `config.ini` so fresh clones use `node` from `PATH`.
- Aligned repository documentation URLs and org branding with VoxHash Technologies / `VoxHash/YTSDownloader`.
- Expanded `.gitignore` for IDE caches, SpecStory history, and local download artifacts.

### Removed
- Stray root markdown files outside the documentation kit (`DEVELOPMENT_GOALS.md`, `GITHUB_TOPICS.md`).

### Fixed
- Documented YouTube bot-check / cookie authentication requirements discovered during fresh-environment validation.

[Unreleased]: https://github.com/VoxHash/YTSDownloader/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.3.4...v0.4.0
[0.3.4]: https://github.com/VoxHash/YTSDownloader/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/VoxHash/YTSDownloader/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/VoxHash/YTSDownloader/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/VoxHash/YTSDownloader/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.4...v0.3.0
[0.2.4]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/VoxHash/YTSDownloader/releases/tag/v0.1.0
