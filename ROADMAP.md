# Roadmap

Current product baseline: **v0.13.0** — Meta Quest 3 **Horizon Store packaging readiness** (2D panel VRC-aligned release manifest / signing / check script) on top of Android multi-worker + SAF cookies + presets (v0.12.0), watermark (v0.11.0), bundled ffmpeg merge (v0.10.0), on-device yt-dlp (v0.9.0), oEmbed titles (v0.8.0), and Quest browse/queue shell (v0.7.x). Desktop Suite remains richest for deep crawl / browser cookie *profiles* (cookies-from-browser).

## Now (v0.13.x)

- [x] **Meta Quest 3** Horizon Store **packaging readiness** (2D panel) — `installLocation=auto`, `excludeFromRecents`, quest `minSdk` 29 / `targetSdk` 34, release signing (v2 via AGP) + `./scripts/check_quest_packaging.sh`; `RELEASE=1 ./scripts/build_quest.sh`. **Not** Store certification / content review / immersive OpenXR. See [docs/quest.md](docs/quest.md).

## Next

_(no active desktop milestone — see Later)_

## Later

### Platforms

- [ ] **Android / GrapheneOS** Suite path — remaining polish beyond slice 5 (deep-crawl browser cookie profiles are desktop-only; on-device path uses exported `cookies.txt`).
- [ ] **Meta Quest 3** immersive OpenXR / Spatial SDK shell — beyond the 2D panel Unknown Sources + packaging-ready release APK; downloads still constrained by store policies and local storage.
- [x] **Meta Quest 3** browse/queue shell (scaffold) — Horizon OS 2D panel product flavor (`quest`); landscape / larger hit targets; inbox `source: quest-companion`; `./scripts/build_quest.sh` + [docs/quest.md](docs/quest.md). Quest ADB install + 2D registration verified (`eureka` / `2G0YC5ZGB6031R`). **On-headset SEND/EXPORT** verified 2026-10-24 after first Unknown Sources open (`SKIP_INSTALL=1 ./scripts/smoke_quest.sh` on-device). Immersive OpenXR **not** done (on-device yt-dlp + ffmpeg merge + watermark + multi-worker/presets/cookies shared with phone flavor via slices 2–5).
- [x] **Meta Quest 3** Horizon Store packaging readiness (2D panel) — see Now (v0.13.0); full Store certification remains out of this checkbox.

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
- Meta Horizon Store **certification / content review** (dashboard submission, VRC full suite beyond packaging markers, policy acceptance for download tooling).
