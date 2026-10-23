# Roadmap

Current product baseline: **v0.3.3** — Optional local analytics counters in the Suite status bar (PyQt6 + yt-dlp).

## Now (v0.3.x)

- [x] Batch export presets (audio-only / video+audio / watermark profiles).
- [x] Per-item failure triage panel with one-click retry.
- [x] Browser media extractor companion notes (extension handoff — desktop remains the downloader).
- [x] Optional analytics counters (success / error / timing) in the status bar.
- [x] Profiled hot-path helpers only if ffmpeg spawn cost shows up in real workloads (keep Python orchestration) — **deferred / no-op**: local profiling (synthetic 2s + 15s watermark paths; live extract attempt) showed process spawn ~tens of ms per call and only a low single-digit–~10% share of watermark wall on a 15s clip; download/extract and re-encode dominate. No native helpers. Revisit if watermark-only batch of long local files becomes primary and spawn (not encode) dominates samples. See `docs/architecture.md` § Language choice.

## Next

- Packaging notes for Windows / macOS / Linux distributables.

## Later

- Deeper social profile crawl modes behind cookie auth (legally constrained surfaces only).

## Out of Scope (for now)

- Cloud sync or hosted download services.
- Copying GPL UI or extractor code into this MIT tree.
- Automated end-to-end CI GUI tests (manual / scripted smoke tests remain the validation path).
