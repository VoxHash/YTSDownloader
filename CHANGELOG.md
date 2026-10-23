# Changelog

All notable changes to `YTSDownloader` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/VoxHash/YTSDownloader/releases/tag/v0.1.0
