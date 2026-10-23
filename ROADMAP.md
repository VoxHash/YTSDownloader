# Roadmap

Current product baseline: **v0.5.0** — optional native sidecars (Rust / C·Zig-cc / Go / Ruby) with Python fallbacks, desktop-friendly process priority, Suite queue triage and volume sidebar.

## Now (v0.5.x)

- [x] Optional hybrid natives: Rust normalize, C/`zig cc` priority helper, Go inbox consumer, Ruby JSON filter — fail soft to Python.
- [x] Bounded workers + optional idle I/O / nice on Start Queue (`PROCESS_IDLE_IO` / `PROCESS_NICE`).
- [x] Deeper social profile crawl modes behind cookie auth (legally constrained surfaces only).
- [x] CI scripted offscreen smoke (`unittest` + `QT_QPA_PLATFORM=offscreen` on GitHub Actions).
- [x] Manual per-OS PyInstaller freeze path complete (`scripts/build_pyinstaller.sh` / `.ps1`, packaging docs, optional Ubuntu-only `freeze.yml` via `workflow_dispatch`).
- [x] Queue context menu (remove / force download), Clear All, and volume sidebar on output-folder Browse.

## Next

- [ ] Bundle or document `native/bin/` next to PyInstaller freezes per OS (optional artifact step).
- [ ] Settings UI surface for native discovery status (`ytscore.native_bridge.native_status`).

## Later

### Platforms

- [ ] **Android / GrapheneOS** app — resolve + queue UX on hardened Android; desktop remains the primary downloader for companion handoff until a dedicated mobile path exists.
- [ ] **Meta Quest 3** app — headset-side browse/queue shell; downloads still constrained by store policies and local storage.

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
