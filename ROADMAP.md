# Roadmap

Current product baseline: **v0.14.0** — Meta Quest 3 **immersive Spatial SDK / OpenXR shell** (panel-in-world hosting the companion UI) plus Android / GrapheneOS **slice 6** polish (Netscape cookie SAF validation, outer retry/backoff, queue resume, Retry row action) on top of Horizon Store packaging readiness (v0.13.0), multi-worker + SAF cookies + presets (v0.12.0), watermark (v0.11.0), bundled ffmpeg merge (v0.10.0), on-device yt-dlp (v0.9.0), oEmbed titles (v0.8.0), and Quest browse/queue shell (v0.7.x). Desktop Suite remains richest for deep crawl / browser cookie *profiles* (cookies-from-browser).

## Now (v0.14.x)

- [x] **Meta Quest 3** immersive OpenXR / Spatial SDK shell — hybrid 2D panel + `ImmersiveShellActivity` (`com.oculus.intent.category.VR`) with Meta Spatial SDK 0.14 ActivityPanel hosting the same companion UI; packaging readiness retained. **Not** Horizon Store immersive certification / content review.
- [x] **Android / GrapheneOS** Suite path — **slice 6** polish beyond slice 5: Netscape `cookies.txt` SAF validation + clearer errors, outer download retry/backoff for transient CDN failures, queue persist resume after process death, per-row Retry. Deep-crawl browser cookie *profiles* remain desktop-only.

## Next

_(no active desktop milestone — see Later)_

## Later

### Platforms

- [ ] **Android / GrapheneOS** further polish — optional extras beyond slice 6 (e.g. richer cookie domain summary UI, download notification channel) if needed; cookies-from-browser profiles stay desktop-only.
- [ ] **Meta Quest 3** Horizon Store **immersive certification** / content review — beyond the first Spatial OpenXR shell + packaging markers.
- [x] **Meta Quest 3** browse/queue shell (scaffold) — Horizon OS 2D panel product flavor (`quest`); landscape / larger hit targets; inbox `source: quest-companion`; `./scripts/build_quest.sh` + [docs/quest.md](docs/quest.md).
- [x] **Meta Quest 3** Horizon Store packaging readiness (2D panel) — see v0.13.0; full Store certification remains out of this checkbox.
- [x] **Meta Quest 3** immersive OpenXR / Spatial SDK shell — see Now (v0.14.0); Store immersive certification remains Later.

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
- Meta Horizon Store **certification / content review** (dashboard submission, VRC full suite beyond packaging markers, policy acceptance for download tooling) — includes immersive Store cert.
