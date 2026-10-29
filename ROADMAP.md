# Roadmap

Current product baseline: **v0.17.2** — resilient YouTube format selection + JS/EJS runtime resolution on top of **v0.17.1** IMPERSONATE Settings UI, **v0.17.0** adult-tube deep crawl extras, **v0.16.0** adult-tube host class + TLS impersonation, **v0.15.2** Desktop Suite free window resize, **v0.15.1** end-to-end install docs, and **v0.15.0** Android slice 7 polish. Desktop Suite remains richest for deep crawl / browser cookie *profiles* (cookies-from-browser).

## Now (v0.17.x)

- [x] **Resilient YouTube formats / EJS** — default `bestvideo*+…` chain + format fallback; `yt-dlp[default]` / ejs; auto-resolve Node (PATH + fnm) so Suite does not fail with storyboard-only “format is not available”.
- [x] **IMPERSONATE Settings UI** — Suite Settings **TLS impersonate** editable combo (`chrome` / empty to disable / other curl_cffi targets); save/reload via `config.ini`; applies to running Settings.
- [x] **Adult-tube deep crawl extras** — paced model/user tabs (`/videos`, `/videos/upload`, `/gifs`, `/photos`); GIF/album listing via clean-room HTML harvest (yt-dlp wrongly collapses those paths); album→photo expand under Deep/Posts; GIF/photo CDN rewrite for download. Cookie-gated deep modes only; no AGPL scrapers in-tree.

## Next

_(no active desktop milestone — see Later)_

## Later

### Platforms

- [x] **IMPERSONATE Settings UI** — see v0.17.1 Now.
- [ ] **Meta Quest 3** Horizon Store **immersive certification** / content review — beyond the first Spatial OpenXR shell + packaging markers.
- [x] **Adult-tube deep crawl extras** — see v0.17.0 Now.
- [x] **Android / GrapheneOS** further polish — see v0.15.0 slice 7; cookies-from-browser profiles stay desktop-only.
- [x] **Meta Quest 3** browse/queue shell (scaffold) — Horizon OS 2D panel product flavor (`quest`); landscape / larger hit targets; inbox `source: quest-companion`; `./scripts/build_quest.sh` + [docs/quest.md](docs/quest.md).
- [x] **Meta Quest 3** Horizon Store packaging readiness (2D panel) — see v0.13.0; full Store certification remains out of this checkbox.
- [x] **Meta Quest 3** immersive OpenXR / Spatial SDK shell — see v0.14.0; Store immersive certification remains Later.
- [x] **Desktop Suite** free window resize — see v0.15.2.
- [x] **Docs / Ops** end-to-end install guides — see v0.15.1.

### Docs / Ops

- [x] End-to-end install + use + cross-platform handoff guides — see Now (v0.15.1).

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
