# Roadmap

Current product baseline: **v0.8.0** — Android / GrapheneOS companion **on-device title resolve + queue UX** (oEmbed) on the phone flavor, plus Meta Quest 3 **browse/queue shell** (v0.7.x). Desktop Suite remains primary downloader. Pixel 7 Pro and Quest 3 ADB handoff paths documented.

## Now (v0.8.x)

- [x] **Android / GrapheneOS** Suite path — **slice 1**: on-device title resolve (YouTube oEmbed + noembed fallback) and queue rows showing title + URL; export payloads may include `title`. On-device yt-dlp download / watermark / full worker parity **not** done — desktop Suite remains the downloader. See [docs/android.md](docs/android.md).

## Next

_(no active desktop milestone — see Later)_

## Later

### Platforms

- [ ] **Android / GrapheneOS** Suite path — remaining: on-device yt-dlp resolve/download workers, watermark, full queue parity with desktop. Companion handoff + oEmbed titles (v0.8.0) are the interim bridge.
- [ ] **Meta Quest 3** immersive / Horizon Store packaging — OpenXR or Spatial SDK beyond the 2D panel Unknown Sources shell; downloads still constrained by store policies and local storage.
- [x] **Meta Quest 3** browse/queue shell (scaffold) — Horizon OS 2D panel product flavor (`quest`); landscape / larger hit targets; inbox `source: quest-companion`; `./scripts/build_quest.sh` + [docs/quest.md](docs/quest.md). Quest ADB install + 2D registration verified (`eureka` / `2G0YC5ZGB6031R`). **On-headset SEND/EXPORT** still needs one manual **Library → Unknown Sources** open after install (Horizon filters cold `am start` / `metavr app launch` with Error type 3; VR passcode + Meta-button Library are not automatable without the Store PIN / worn session). Smoke falls back to Pixel with the same Quest APK. Immersive OpenXR / Horizon Store / on-device download **not** done.

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
