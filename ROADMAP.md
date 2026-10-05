# Roadmap

Current product baseline: **v0.1.0** — PyQt6 multi-platform downloader with optional watermarking via yt-dlp + moviepy.

## Now (v0.1.x)

- Keep extractor auth guidance accurate for YouTube bot checks (cookies / JS runtime).
- Improve startup messaging when `ffmpeg` or the configured JS runtime is missing.
- Reduce GUI shutdown / logging-handler edge cases on close.

## Next

- Reusable watermark and export presets.
- Clearer per-item batch progress and failure reporting.
- Safer retries for temporary network/extractor failures.

## Later

- Lightweight download analytics (success/error counts, timing).
- Optional settings UI for auth and runtime options currently limited to `config.ini`.
- Packaging notes for Windows / macOS / Linux distributables.

## Out of Scope (for now)

- Cloud sync or hosted download services.
- Automated end-to-end CI GUI tests (manual smoke tests remain the validation path).
