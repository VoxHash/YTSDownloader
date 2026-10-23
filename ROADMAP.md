# Roadmap

Current product baseline: **v0.3.0** — Batch export presets (PyQt6 + yt-dlp).

## Now (v0.3.x)

- [x] Batch export presets (audio-only / video+audio / watermark profiles).

## Next

- Per-item failure triage panel with one-click retry.
- Browser media extractor companion notes (extension handoff — desktop remains the downloader).
- Optional analytics counters (success / error / timing) in the status bar.

## Later

- Profiled hot-path helpers only if ffmpeg spawn cost shows up in real workloads (keep Python orchestration).
- Packaging notes for Windows / macOS / Linux distributables.
- Deeper social profile crawl modes behind cookie auth (legally constrained surfaces only).

## Out of Scope (for now)

- Cloud sync or hosted download services.
- Copying GPL UI or extractor code into this MIT tree.
- Automated end-to-end CI GUI tests (manual / scripted smoke tests remain the validation path).
