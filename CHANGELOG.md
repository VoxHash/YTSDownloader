# Changelog

All notable changes to `YTSDownloader` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.15.1] - 2026-10-25

### Added
- **Docs / Ops:** end-to-end install + use guides for Android / GrapheneOS, Meta Quest 3, and Desktop Suite; new [docs/cross-platform.md](docs/cross-platform.md) for companion inbox handoff (NDJSON schema v1, `.ytsdownloader/inbox/`, ~1.5s polling, Export to Downloads → Suite enqueue).

### Changed
- Restructured [docs/android.md](docs/android.md) and [docs/quest.md](docs/quest.md) into Install → Use after install flows (real package IDs, intents, paths).
- [docs/installation.md](docs/installation.md) / [docs/usage.md](docs/usage.md) / [docs/index.md](docs/index.md) / README linked for post-install Suite and cross-platform paths.
- ROADMAP: Docs/Ops milestone checked under Now (v0.15.1).
- Version bump: desktop `ytscore` + Android `versionName`/`versionCode` → **0.15.1** / 12.

## [0.15.0] - 2026-10-25

### Added
- **Android / GrapheneOS slice 7 polish:** richer Netscape cookie **domain summary** in the cookie row (unique domains + top domains × counts); local **download notification channel** (`yts_downloads`) with progress / done / error posts; `POST_NOTIFICATIONS` runtime request on first download (API 33+). No FCM / Play Services.
- Host tests: cookie domain extract/format (`tests/test_android_cookie_bundle.py`), notification id / channel markers (`tests/test_android_download_notifier.py`).

### Changed
- ROADMAP: v0.15.0 Android slice 7 checked; Horizon Store immersive certification remains Later / out of scope (not claimed).
- Docs: [docs/android.md](docs/android.md) slice 7 cookie domain + notification notes.
- Version bump: desktop `ytscore` + Android `versionName`/`versionCode` → **0.15.0** / 11.

### Verified
- Host: Suite `unittest discover` (incl. cookie domain + download notifier + quest packaging).
- Pixel 7 Pro (`29211FDH300NEB` / cheetah) and Quest 3 (`2G0YC5ZGB6031R` / eureka) device smoke when present on farm ADB.

## [0.14.0] - 2026-10-25

### Added
- **Meta Quest 3 immersive Spatial SDK / OpenXR shell:** hybrid app — keep 2D panel `MainActivity` (`com.oculus.intent.category.2D`) and add `ImmersiveShellActivity` (`com.oculus.intent.category.VR`) using Meta Spatial SDK **0.14** (`VRFeature` + `ActivityPanelRegistration` panel-in-world hosting the same companion UI). Quest UI **Enter immersive** button + ADB `OPEN_IMMERSIVE`. Horizon OS SDK marker + `libossdk.oculus.so`. **Not** Store immersive certification.
- **Android / GrapheneOS slice 6 polish:** Netscape `cookies.txt` SAF validation with clearer import errors + cookie-row summary; outer yt-dlp download retry/exponential backoff for transient CDN / SSL / 429 failures; queue persist uses `commit()` and resumes QUEUED/DOWNLOADING after process death; per-row **Retry** on error.
- Host tests: immersive packaging markers (`tests/test_quest_packaging.py`), cookie Netscape validation (`tests/test_android_cookie_bundle.py`), worker backoff helpers (`tests/test_android_ytdlp_worker.py`).

### Changed
- ROADMAP: v0.14.0 Quest immersive shell + Android slice 6 checked; Store immersive certification and further optional polish remain Later.
- Docs: [docs/quest.md](docs/quest.md) hybrid immersive path; [docs/android.md](docs/android.md) slice 6 cookie / retry / resume notes.
- Version bump: desktop `ytscore` + Android `versionName`/`versionCode` → **0.14.0** / 10.
- `./scripts/check_quest_packaging.sh` + `./scripts/smoke_quest.sh` assert VR / ImmersiveShellActivity markers.

### Verified
- Host: Suite `unittest discover` (incl. quest packaging + Android worker/cookie tests).
- Quest 3 (`2G0YC5ZGB6031R` / eureka) and Pixel 7 Pro (`29211FDH300NEB` / cheetah) device smoke when present on farm ADB.

## [0.13.0] - 2026-10-24

### Added
- **Meta Quest 3 Horizon Store packaging readiness (2D panel):** quest release path (`RELEASE=1 ./scripts/build_quest.sh`); `installLocation=auto`, `excludeFromRecents`, quest flavor `minSdk` 29 / `targetSdk` 34; release signing config (env upload keystore or debug-keystore fallback, AGP v2+); `./scripts/check_quest_packaging.sh` (manifest markers, size, `apksigner`, aapt badging).
- Host tests for packaging source markers + check-script gate (`tests/test_quest_packaging.py`).

### Changed
- ROADMAP: v0.13.0 Quest Store packaging readiness checked; immersive OpenXR / Store **certification** remain Later / out of scope.
- Docs: [docs/quest.md](docs/quest.md) packaging table, release build, signing env vars; honesty that certification is not claimed.
- Version bump: desktop `ytscore` + Android `versionName`/`versionCode` → **0.13.0** / 9.

### Verified
- Host: Suite `unittest discover` **109** tests green (incl. `test_quest_packaging` + Android worker suite).
- `RELEASE=1 ./scripts/build_quest.sh` → `app-quest-release.apk` (~43 MB); `./scripts/check_quest_packaging.sh` passed (manifest markers, minSdk 29 / targetSdk 34, arm64-v8a, apksigner v2+).
- Quest 3 (`2G0YC5ZGB6031R` / eureka): release APK install + on-device SEND/EXPORT smoke passed (`./scripts/smoke_quest.sh`).

## [0.12.0] - 2026-10-24

### Added
- **Android Suite path (slice 5):** bounded multi-worker downloads (1–4, default 2); Netscape `cookies.txt` via SAF (`CookieBundle`, no Play Services); export presets `audio_only` / `video_audio` / `watermark` wired into `yts_dlp_worker` + UI spinners; ADB `--es yts_preset` / `--ei yts_max_workers`.
- Host tests for preset resolve, audio-only download, and missing-cookiefile ignore (`tests/test_android_ytdlp_worker.py`).
- Smoke extras: `PRESET=…` / `MAX_WORKERS=…` in `./scripts/smoke_android_download.sh`.

### Changed
- ROADMAP: v0.12.0 Android multi-worker / cookie + format-preset parity checked; desktop remains richest for deep crawl / cookies-from-browser profiles.
- Docs: [docs/android.md](docs/android.md) / [docs/quest.md](docs/quest.md) honesty on workers, presets, SAF cookies.
- Version bump: desktop `ytscore` + Android `versionName`/`versionCode` → **0.12.0** / 8.

### Verified
- Host: full Suite `unittest discover` green (incl. Android worker preset / audio / watermark / cookie-miss).
- Pixel 7 Pro (`29211FDH300NEB` / cheetah, `ANDROID_ADB_SERVER_PORT=5137`): `video_audio`, `PRESET=audio_only`, and `WATERMARK=1` / `PRESET=watermark` download smokes passed (`.mp4` / `.m4a` / `*_wm.mp4` under app Movies). Occasional on-device CDN `Errno 104` / SSL timeouts remain intermittent under farm USB load.

## [0.11.0] - 2026-10-24

### Added
- **Android Suite path (slice 4):** optional full-frame PNG watermark overlay via bundled LGPL ffmpeg (`WatermarkBundle` + `apply_watermark` in `yts_dlp_worker`); UI switch + ADB `--ez yts_watermark true`; bundled `assets/watermark/default_watermark.png`.
- Host tests for watermark composite + download-with-watermark (`tests/test_android_ytdlp_worker.py`).
- `WATERMARK=1` support in `./scripts/smoke_android_download.sh`.

### Changed
- ROADMAP: v0.11.0 Android watermark overlay checked; Quest on-headset SEND/EXPORT verified 2026-10-24 after Unknown Sources open.
- Docs: [docs/android.md](docs/android.md) / [docs/quest.md](docs/quest.md) honesty on watermark + Quest smoke.
- Version bump: desktop `ytscore` + Android `versionName`/`versionCode` → **0.11.0** / 7.

### Verified
- Quest 3 (`2G0YC5ZGB6031R` / eureka, `ANDROID_ADB_SERVER_PORT=5137`): cold `am start` / monkey / SEND / EXPORT on-device after Unknown Sources gate cleared; `SKIP_INSTALL=1 ./scripts/smoke_quest.sh` passed.
- Pixel 7 Pro (`29211FDH300NEB` / cheetah): watermark download smoke (`WATERMARK=1 ./scripts/smoke_android_download.sh`) when device present.

## [0.10.0] - 2026-10-24

### Added
- **Android Suite path (slice 3):** bundled arm64-v8a LGPL ffmpeg (FFmpeg 8.1.1, `--disable-gpl`) via `scripts/fetch_android_ffmpeg.sh` + `FfmpegBundle`; yt-dlp prefers `bestvideo+bestaudio` merge with `merge_output_format=mp4` when the binary is available, else single-file fallback.
- Host tests for merge vs single-file format selection and merge download with system ffmpeg (`tests/test_android_ytdlp_worker.py`).

### Changed
- ROADMAP: v0.10.0 Android ffmpeg merge checked; Pixel on-device download smoke verified 2026-10-24; Quest on-headset SEND still blocked by Horizon Error type 3 / empty a11y until manual Unknown Sources open.
- Docs: [docs/android.md](docs/android.md) / [docs/quest.md](docs/quest.md) honesty on merge + device smoke.
- Version bump: desktop `ytscore` + Android `versionName`/`versionCode` → **0.10.0** / 6.

### Verified
- Pixel 7 Pro (`29211FDH300NEB` / cheetah): `./scripts/smoke_android_download.sh` → media under app `Movies/YTSCompanion/` (complete `.mp4`), no `FATAL EXCEPTION`.
- Quest 3 (`2G0YC5ZGB6031R` / eureka, farm ADB port): install + 2D registration OK; cold `am start` / SEND still **Error type 3**; uiautomator hierarchy empty (VR shell only).

## [0.9.0] - 2026-10-24

### Added
- **Android Suite path (slice 2):** on-device yt-dlp download via Chaquopy (Python 3.12 + pinned `yt-dlp==2026.10.21`); queue status + per-row / **Download queue** actions; media under app `Movies/YTSCompanion/`; ADB action `dev.voxhash.ytscompanion.action.DOWNLOAD_QUEUE`.
- `./scripts/smoke_android_download.sh` — install + SEND + DOWNLOAD_QUEUE smoke (Pixel serial preferred; farm-port scan for `cheetah`).
- Host unit coverage for the Android `yts_dlp_worker` module (`tests/test_android_ytdlp_worker.py`).

### Changed
- ROADMAP: v0.9.0 Android yt-dlp single-file download checked; watermark / ffmpeg merge / full desktop parity stays Later.
- Docs: [docs/android.md](docs/android.md) download path + honesty on single-file limits.
- Version bump: desktop `ytscore` + Android `versionName`/`versionCode` → **0.9.0** / 5.

## [0.8.0] - 2026-10-23

### Added
- **Android Suite path (slice 1):** on-device title resolve via YouTube oEmbed + noembed fallback; queue rows show title + URL; export JSON/JSONL may include `title` (`INTERNET` permission).
- Docs: [docs/quest.md](docs/quest.md) on-headset smoke matrix (prox_close / VR passcode / Unknown Sources gate); smoke script tries `prox_close` + `cmd package unstop` before `am start`.

### Changed
- ROADMAP: v0.8.0 Android resolve+queue UX checked; remaining on-device yt-dlp/download stays Later. Quest on-headset SEND/EXPORT still needs one manual Unknown Sources open.
- Version bump: desktop `ytscore` + Android `versionName`/`versionCode` → **0.8.0** / 4.

## [0.7.0] - 2026-10-23

### Added
- **Meta Quest 3** companion shell: Android product flavor `quest` (Horizon OS 2D panel) — package-aligned `dev.voxhash.ytscompanion.quest.MainActivity`, landscape layout, larger hit targets, inbox `source: quest-companion`, `com.oculus.intent.category.2D` / `supportedDevices` metadata.
- `./scripts/build_quest.sh`, `./scripts/smoke_quest.sh` (Quest install + 2D registration; SEND/EXPORT with Pixel fallback when Horizon blocks cold `am start`).
- Docs: [docs/quest.md](docs/quest.md).

### Changed
- Android Gradle split into `phone` + `quest` flavors; phone APK path is now `android/app/build/outputs/apk/phone/debug/app-phone-debug.apk` (`./scripts/build_android.sh`).
- ROADMAP: Quest browse/queue shell scaffold marked done; immersive / Store packaging stays Later. Pixel Share+SAF notes remain in [docs/android.md](docs/android.md).

## [0.6.2] - 2026-10-23

### Added
- Android companion **Export to Downloads**: writes schema-1 `android-companion` JSON to MediaStore `Download/YTSCompanion/` and app-specific `files/Download/` without SAF or share chooser; ADB action `dev.voxhash.ytscompanion.action.EXPORT_DOWNLOADS` (or `--ez yts_export_downloads true`).

### Changed
- ROADMAP / [docs/android.md](docs/android.md): Pixel handoff verified via Downloads export; note Android 17 `uiautomator dump` / SAF-chooser automation limits.

## [0.6.1] - 2026-10-23

### Changed
- ROADMAP: Pixel 7 Pro ADB smoke e2e marked done (`cheetah` install / launch / SEND+VIEW queue / prefs / no package FATAL).
- [docs/android.md](docs/android.md): multi-`adb`-server USB farm troubleshooting when Pixel appears in `lsusb` but not default `adb devices`; ADB SEND smoke snippet.

## [0.6.0] - 2026-10-23

### Added
- **Android companion** (`android/`): Kotlin / Material app for GrapheneOS-friendly ADB sideload — local URL queue (paste + `ACTION_SEND`), Storage Access Framework export folder / create-document, share NDJSON/JSON inbox payloads for the desktop Suite. No Google Play Services / FCM; cleartext HTTP disabled by default.
- `./scripts/build_android.sh` — fish-safe debug APK build helper (`JAVA_HOME` JDK 17, `ANDROID_HOME`).
- Docs: [docs/android.md](docs/android.md) (build, GrapheneOS install, smoke checklist, parity disclaimer).

### Changed
- ROADMAP: companion scaffold marked done under Now; full Android Suite path stays Later; Pixel 7 Pro e2e tracked until that device appears on ADB.

## [0.5.2] - 2026-10-23

### Added
- Suite **Settings** panel **Native helpers**: shows `YTS_USE_NATIVE`, search directory, and discovery paths for normalize / priority / inbox / Ruby filter sidecars (or honest Python-fallback text when missing/disabled), with **Refresh** to re-scan.
- Offscreen / unit coverage for the native status Settings surface (`tests/test_native_bridge.py`).

### Changed
- SuiteDark styles for the native status panel; configuration docs mention the Settings discovery UI.

## [0.5.1] - 2026-10-23

### Added
- PyInstaller freeze helpers auto-bundle `native/bin/` into `dist/YTSDownloader/native/bin/` when present (`BUNDLE_NATIVES=auto|1|0` on `scripts/build_pyinstaller.sh` / `.ps1`).
- `ytscore.native_bridge` discovers freeze-adjacent and cwd `native/bin/` (plus `YTS_NATIVE_DIR` / checkout).
- Optional `freeze.yml` input **bundle natives** (best-effort `gcc` / Go build into the Ubuntu onedir artifact).

### Changed
- Packaging docs describe the onedir `native/bin/` layout and `BUNDLE_NATIVES` knobs.

## [0.5.0] - 2026-10-23

### Added
- Optional **native sidecars** with Python fallbacks: Rust `yts-normalize` (batch URL/path normalize), C/`zig cc` `yts-prio` (nice + Linux idle I/O), Go `yts-inbox` (concurrent companion inbox), Ruby `yts_json_filter.rb` (companion JSON filter).
- `scripts/build_natives.sh`, `ytscore.native_bridge` / `normalize` / `process_prio`, Settings keys `PROCESS_NICE` / `PROCESS_IDLE_IO`, env `YTS_USE_NATIVE` / `YTS_NATIVE_DIR`.
- Unit tests for IPC discovery, fallbacks, and offscreen Suite without natives (`tests/test_native_bridge.py`).
- Docs: architecture language map, installation native build/packaging notes; ROADMAP **Platforms** (Android / GrapheneOS, Meta Quest 3) and deferred native items.

### Changed
- `DownloadQueue.add_many` batch-normalizes URLs; `start` may apply desktop-friendly process priority.
- Companion inbox prefers Go consume when built; structured payloads may use Ruby filter first.

## [0.4.5] - 2026-10-23

### Added
- Output-folder dialog sidebar includes the local system root (`/` as **Computer**) by default, ahead of `/run/media` / `/media` / `/mnt` volume mounts.

### Fixed
- Folder-dialog sidebar no longer omits the primary local disk when only external/cloud mounts were listed.

## [0.4.4] - 2026-10-23

### Added
- Original Suite-dark app icon (`assets/icons/`, SVG + 32–256 PNG); wired via `QApplication` / window icon, `scripts/install_local.sh` → `~/.local/share/icons/hicolor`, and PyInstaller `--icon` / `assets` bundle.

### Changed
- Output-folder dialog sidebar lists **volume/mount roots only** (`/run/media/$USER`, `/media/$USER`, `/mnt` mounts from `/proc/mounts`). Home / Downloads / Desktop / Documents / Music / Pictures / Videos / Trash are no longer sidebar entries; empty `/mnt` stubs (e.g. `/mnt/test`) are skipped.

### Fixed
- Folder-dialog sidebar no longer surfaces Qt/XDG user places or non-mount `/mnt` placeholders.

## [0.4.3] - 2026-10-23

### Added
- Queue row context menu: **Remove from queue** and **Force download** (prioritize + start immediately, skip pacing; works while queue is stopped).
- **Clear All** next to Clear Finished (confirm dialog; persists empty `queue_state.json`).
- Output-folder picker sidebar for Home / Downloads / `/run/media` / `/media` / `/mnt` and mounts from `/proc/mounts` (`ytscore.folder_dialog`); Linux uses Qt dialog so volumes stay visible. Applied to Download Browse and Settings default output.
- `scripts/install_local.sh` — single user-local Linux install (`~/.local/bin/ytsdownloader` + `.desktop`); docs in [installation.md](docs/installation.md#local-desktop-install-linux).
- Unit / offscreen tests for remove, clear all, force download, and folder sidebar helpers.

### Changed
- `DownloadQueue.start` submits any still-queued jobs not already in flight (safe after a force-download bootstrap).

## [0.4.2] - 2026-10-23

### Added
- `scripts/build_pyinstaller.ps1` — Windows PowerShell freeze helper (same onedir flags as the bash script; copies `config.ini` / `themes/` next to the binary).
- Optional GitHub Actions **Freeze (manual)** workflow (`.github/workflows/freeze.yml`): `workflow_dispatch` only, Ubuntu onedir + artifact; not a required PR check.
- Packaging docs: consistent Linux / macOS / Windows recipes, `YTS_PYTHON` / `SMOKE=1` notes, checklist item for helper scripts.

### Changed
- `scripts/build_pyinstaller.sh` accepts `YTS_PYTHON` and optional `SMOKE=1` offscreen launch smoke (Linux/macOS).
- Roadmap: manual per-OS freeze path marked done under Now; **required** cross-OS freeze CI matrix stays out of scope.

## [0.4.1] - 2026-10-23

### Added
- GitHub Actions **CI** workflow (`.github/workflows/ci.yml`): on push/PR, install Qt runtime libs on Ubuntu, set `QT_QPA_PLATFORM=offscreen`, run `python -m unittest discover -s tests` across Python 3.10 / 3.12 / 3.14.
- Docs: CONTRIBUTING / troubleshooting / getting-started / PR template describe the scripted offscreen validation path (fish-safe `.venv/bin/python`).

### Changed
- Roadmap: CI scripted offscreen smoke marked done; headed GUI e2e click farms stay out of scope. Manual GUI smoke remains optional for release checks.

## [0.4.0] - 2026-10-23

### Added
- **Profile / channel crawl modes** behind cookie auth (`ytscore.crawl`): Shallow, Deep (multi-tab), Videos, Shorts, and Posts — deep modes require `COOKIES_FROM_BROWSER` or `COOKIES_FILE`.
- Download Suite controls: crawl mode combo + item limit (1–500); Resolve / drop / Link Grabber use the selected mode with pacing between tab fetches and backoff on rate-limit signals.
- Auth-gate hint on Download; deep crawl enumerates only surfaces the signed-in session can already reach via existing extractors (no paywall/DRM bypass).
- Unit tests and offscreen Suite smoke for crawl helpers, auth gate, and UI wiring.

### Changed
- SemVer minor bump: first shipped item from the former **Later** wave after the v0.3.x packaging baseline.
- Roadmap: cookie-auth profile crawl completed; Next / Later empty.
- Docs: usage, API, architecture, configuration, README cover crawl modes.

## [0.3.4] - 2026-10-23

### Added
- **Packaging notes** for Windows / macOS / Linux distributables: PyInstaller `onedir` primary recipe, ffmpeg/ffprobe as external PATH deps, optional Briefcase wrap, cx_Freeze called out as alternative.
- `scripts/build_pyinstaller.sh` — fish-safe local freeze helper (no venv activate required).

### Changed
- Docs kit: installation, getting-started, architecture, FAQ, troubleshooting, index, and README link the packaging section.
- Roadmap: packaging milestone completed; Next is empty (Later: deeper cookie-auth profile crawl).
- Architecture: ffmpeg spawn profiling on synthetic watermark paths — **no native hot-path helpers**; spawn is not a meaningful share of realistic Suite wall time.

### Fixed
- Parse `COUNT_TIMER_ONGOING` as float in `main.py` so the default `2.5` pacing value does not crash import (required for Suite and frozen launches).

## [0.3.3] - 2026-10-23

### Added
- Optional **local session analytics** in the Suite status bar: success count, error count, last job duration, and session average duration.
- Settings checkbox **Show analytics in status bar** (`SHOW_STATUS_ANALYTICS` in `config.ini`); default on; no network telemetry.
- `ytscore.analytics.SessionAnalytics` helpers plus unit / offscreen Suite smoke tests.

### Changed
- Settings hint documents local-only analytics; configuration / API / usage docs updated.

## [0.3.2] - 2026-10-23

### Added
- Browser **companion inbox** handoff: Suite polls `.ytsdownloader/inbox/` and `.ytsdownloader/companion_inbox.jsonl` for media URLs; desktop remains the only downloader.
- `ytscore.companion` parsers (`parse_companion_payload`, `consume_companion_inbox`) plus unit / offscreen Suite smoke tests.
- Architecture docs for the extension handoff contract (drop zone + Link Grabber + local inbox); docs index / usage / API / configuration updated.

### Changed
- Download page hint mentions the companion inbox path.

## [0.3.1] - 2026-10-23

### Added
- Queue **Failure triage** panel: select a row to see classified error category (rate limit / auth / network / unavailable / format / unknown) and full detail.
- **Retry selected** and **Retry failed** actions re-queue jobs cleanly (reset state/progress/error; preserve URL, title, media, and export options).
- `ytscore.triage` classifiers and `DownloadQueue.retry_jobs` / `retry_failed` helpers with unit / offscreen Suite smoke tests.

### Changed
- SuiteDark styles for the triage panel; Queue hint documents triage + retry.

## [0.3.0] - 2026-10-23

### Added
- Named **export presets** on Download: Audio only, Video + audio, Watermark, and Custom — choosing a preset sets media / container / watermark options for newly enqueued jobs.
- Queue **Apply to selected** / **Apply to queued** to batch-update export options on pending items; Export column shows audio / video / video+wm / search audio.
- Per-job `watermark_path` and `output_format` on the download queue (persisted in queue JSON); download pipeline prefers per-job options over queue defaults.
- `ytscore.presets` helpers and unit / offscreen Suite smoke tests.

### Changed
- SemVer minor bump: first shipped item from the former **Next** wave after the v0.2.x Settings / persistence baseline.

## [0.2.4] - 2026-10-23

### Added
- Suite **Settings** form edits the real `config.ini` keys (theme, cookies, JS runtime, workers/retries, pace, backoff, formats, default output) with atomic write via `ytscore.settings.save_settings`.
- Save applies into the running `Settings` / queue object without a full restart (pace, backoff, cookies, formats, retries); worker count takes effect on the next Start Queue.
- Unit tests for write/read round-trip and offscreen Settings UI smoke.

### Changed
- Settings page is no longer reload-only; Reload still refreshes the form from disk.

## [0.2.3] - 2026-10-23

### Added
- Local **queue persistence** to `.ytsdownloader/queue_state.json` (gitignored): saves on enqueue/state changes, Clear Finished, and app close; restores on Suite startup.
- Safer restore: in-progress (`running`) items become **queued** with a “press Start Queue to resume” message — downloads are **not** auto-restarted.

### Changed
- **Clear Finished** removes done/failed/cancelled jobs from the queue engine (and persisted state), not only from the table view.
- Queue page hint documents restore-without-auto-start behavior.

## [0.2.2] - 2026-10-23

### Added
- Shared playlist **start-slot pacing** so concurrent queue workers space job starts by `COUNT_TIMER_ONGOING`.
- Rate-limit-aware **exponential backoff** on download retries (`BACKOFF_BASE`, `BACKOFF_FACTOR`, `BACKOFF_MAX`); HTTP 429 / rate-limit errors use a harder base and extend the global queue cooldown.
- `ytscore.backoff` helpers for detection and delay calculation (unit-tested without live hosts).

### Changed
- Default playlist pace raised to **2.5s** (`COUNT_TIMER_ONGOING`).
- Suite Settings overview shows pace and backoff knobs.
- Retry waits no longer cap at a flat 8s; they follow configured exponential backoff (max 90s by default).

## [0.2.1] - 2026-10-23

### Added
- Queue page filters: state combo (All / queued / running / done / failed / cancelled) and text search over title, URL, and message.
- Download page drag-and-drop URL zone (browser links or `.txt` / `.url` files); single drop fills the URL field, multiple URLs resolve into the queue.
- `extract_urls` helper in `ytscore.util` for paste/drop parsing.

### Changed
- SuiteDark styles for the drop zone (dashed target, green highlight while dragging).

## [0.2.0] - 2026-10-23

### Added
- Modular core package (`ytscore`): settings, resolvers, concurrent download queue with retries, downloader, watermark, metadata bridge.
- Suite GUI (`ytsgui`): sidebar navigation, download page, queue table, link grabber, metadata bridge, settings overview.
- SuiteDark theme with dark hierarchy and queue-focused layout.
- Metadata bridge reads the local music desktop session (MPRIS on Linux) and queues matching public-host audio downloads.
- Config knobs: `MAX_WORKERS`, `MAX_RETRIES`, `AUDIO_FORMAT`, `VIDEO_FORMAT`, `DEFAULT_OUTPUT`.
- `python main.py --legacy` keeps the classic tabbed window.

### Changed
- Default entrypoint launches the Suite UI.
- Default theme set to `SuiteDark`.
- Architecture docs updated for the modular layout.
- Docs prefer shell-agnostic `.venv/bin/python` / `.venv/bin/pip` (and `./run.sh`); fish users should use `activate.fish`, not bash `activate`.

## [0.1.0] - 2026-10-05

### Added
- PyQt6 desktop workflow for multi-platform short-video downloading (YouTube, Instagram, Facebook, TikTok).
- Watermarking pipeline with moviepy and Pillow.
- Runtime configuration in `config.ini` for theme, cookies, and JS runtime.
- Standardized documentation kit (`README`, `CONTRIBUTING`, `ROADMAP`, `CHANGELOG`, `CODE_OF_CONDUCT`, `SECURITY`, `SUPPORT`, `docs/`).
- GitHub issue and pull request templates.

### Changed
- Cleared machine-specific `JS_RUNTIME_PATH` from the default `config.ini` so fresh clones use `node` from `PATH`.
- Aligned repository documentation URLs and org branding with VoxHash Technologies / `VoxHash/YTSDownloader`.
- Expanded `.gitignore` for IDE caches, SpecStory history, and local download artifacts.

### Removed
- Stray root markdown files outside the documentation kit (`DEVELOPMENT_GOALS.md`, `GITHUB_TOPICS.md`).

### Fixed
- Documented YouTube bot-check / cookie authentication requirements discovered during fresh-environment validation.

[Unreleased]: https://github.com/VoxHash/YTSDownloader/compare/v0.15.1...HEAD
[0.15.1]: https://github.com/VoxHash/YTSDownloader/compare/v0.15.0...v0.15.1
[0.15.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.14.0...v0.15.0
[0.14.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.13.0...v0.14.0
[0.13.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.12.0...v0.13.0
[0.12.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.6.2...v0.7.0
[0.6.2]: https://github.com/VoxHash/YTSDownloader/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/VoxHash/YTSDownloader/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.5.2...v0.6.0
[0.5.2]: https://github.com/VoxHash/YTSDownloader/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/VoxHash/YTSDownloader/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.4.5...v0.5.0
[0.4.5]: https://github.com/VoxHash/YTSDownloader/compare/v0.4.4...v0.4.5
[0.4.4]: https://github.com/VoxHash/YTSDownloader/compare/v0.4.3...v0.4.4
[0.4.3]: https://github.com/VoxHash/YTSDownloader/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/VoxHash/YTSDownloader/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/VoxHash/YTSDownloader/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.3.4...v0.4.0
[0.3.4]: https://github.com/VoxHash/YTSDownloader/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/VoxHash/YTSDownloader/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/VoxHash/YTSDownloader/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/VoxHash/YTSDownloader/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.4...v0.3.0
[0.2.4]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/VoxHash/YTSDownloader/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/VoxHash/YTSDownloader/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/VoxHash/YTSDownloader/releases/tag/v0.1.0
