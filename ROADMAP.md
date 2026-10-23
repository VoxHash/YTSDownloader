# Roadmap

Current product baseline: **v0.2.1** — Suite UI polish (queue filters + URL drop zone) on the modular download suite (PyQt6 + yt-dlp).

## Now (v0.2.x)

- [x] Suite UI polish: filters on the queue table, drag-and-drop URL drop zone.
- Stronger playlist pacing and rate-limit backoff defaults.
- Persist queue state across restarts (local JSON).
- Settings page write-back to `config.ini` (today: reload-only).

## Next

- Batch export presets (audio-only / video+audio / watermark profiles).
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
