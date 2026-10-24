# Roadmap

Current product baseline: **v0.11.0** — Android / GrapheneOS companion **optional PNG watermark overlay** (slice 4) on top of bundled ffmpeg merge (v0.10.0), on-device yt-dlp (v0.9.0), oEmbed titles (v0.8.0), and Meta Quest 3 **browse/queue shell** (v0.7.x). Desktop Suite remains the richest downloader (multi-worker / cookie + format-preset parity still later).

## Now (v0.11.x)

- [x] **Android / GrapheneOS** Suite path — **slice 4**: optional full-frame PNG watermark overlay via bundled LGPL ffmpeg (`WatermarkBundle` + worker `apply_watermark`); UI switch + ADB `--ez yts_watermark true`. Pixel 7 Pro watermark download smoke verified (2026-10-24). Multi-worker / cookie + format-preset parity **not** done. See [docs/android.md](docs/android.md).

## Next

_(no active desktop milestone — see Later)_

## Later

### Platforms

- [ ] **Android / GrapheneOS** Suite path — remaining: desktop-class multi-worker / format presets / cookie parity. Slices 1–4 (oEmbed + yt-dlp + ffmpeg merge + watermark overlay) ship as the on-device bridge.
- [ ] **Meta Quest 3** immersive / Horizon Store packaging — OpenXR or Spatial SDK beyond the 2D panel Unknown Sources shell; downloads still constrained by store policies and local storage.
- [x] **Meta Quest 3** browse/queue shell (scaffold) — Horizon OS 2D panel product flavor (`quest`); landscape / larger hit targets; inbox `source: quest-companion`; `./scripts/build_quest.sh` + [docs/quest.md](docs/quest.md). Quest ADB install + 2D registration verified (`eureka` / `2G0YC5ZGB6031R`). **On-headset SEND/EXPORT** verified 2026-10-24 after first Unknown Sources open (`SKIP_INSTALL=1 ./scripts/smoke_quest.sh` on-device). Immersive OpenXR / Horizon Store **not** done (on-device yt-dlp + ffmpeg merge + watermark now shared with phone flavor via slices 2–4).

### Native / core (deferred with rationale)

- [ ] Pure-Zig `build-exe` rewrite of `yts-prio` — deferred while Zig 0.17 process/Io and `@cImport` settle; **`zig cc` on the C sources** is the supported Zig toolchain path today.
- [ ] Cross-process Rust slot-broker sidecar — deferred; in-process `ThreadPoolExecutor` + `MAX_WORKERS` already bounds concurrency; no measured multi-process win yet.
- [ ] Native watermark preprocess (Zig/C) — deferred; profiling shows encode cost dominates spawn/preprocess.
- [ ] Go download workers — deferred; downloads are I/O-bound and yt-dlp stays Python.

## Out of Scope (for now)

- Cloud sync or hosted download services.
- Copying GPL UI or extractor code into this MIT tree.
- Automated headed end-to-end GUI CI (display / Xvfb Suite click farms). Validation path: local + CI **scripted offscreen** unit/smoke under `tests/`, plus optional manual GUI checks before release.
- **Required** cross-OS freeze CI matrix on every PR (ubuntu + windows + macos as required checks). Manual per-OS freezes first; optional best-effort Ubuntu freeze is `workflow_dispatch` only — see packaging docs. Do not claim a green required matrix while hosted runners are flaky or signing/ffmpeg per OS is unfinished.
