# Changelog

All notable changes to `YTSDownloader` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/VoxHash/YTSDownloader/releases/tag/v0.1.0
