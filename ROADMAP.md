# Roadmap

Current product baseline: **v0.6.2** — Android companion scaffold (`android/`) ships: paste/share URL queue + SAF/share + **Export to Downloads** (ADB-pullable) inbox export for desktop handoff. Desktop Suite remains primary. Pixel 7 Pro Share/SAF→inbox handoff verified via Downloads export (`cheetah` / `29211FDH300NEB`).

## Now (v0.6.x)

- [x] Android / GrapheneOS **companion scaffold** — Kotlin app under `android/`; queue + paste/share; SAF export / share payload matching desktop inbox contract; no Play Services / FCM; cleartext off. Docs: [docs/android.md](docs/android.md). Full Suite feature parity **not** done.
- [x] Pixel 7 Pro ADB smoke e2e — install / launch / `ACTION_SEND` + `ACTION_VIEW` URL queue / prefs persistence / no package FATAL (`product:cheetah` / `model:Pixel_7_Pro`). SAF folder pick + Share chooser remain manual on-device taps.
- [x] Pixel 7 Pro companion inbox handoff — **Export to Downloads** (`EXPORT_DOWNLOADS` / MediaStore `Download/YTSCompanion/`) → `adb pull` → `.ytsdownloader/inbox/` → desktop `consume_companion_inbox` accepts `schema: 1` / `source: android-companion`.

## Next

_(no active desktop milestone — see Later)_

## Later

### Platforms

- [ ] **Android / GrapheneOS** full Suite path — on-device resolve + queue UX on hardened Android; desktop remains primary until that dedicated path exists. Companion handoff (v0.6.0 scaffold) is the interim bridge.
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
