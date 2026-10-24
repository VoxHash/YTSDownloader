# Android companion (GrapheneOS-friendly)

Lightweight **Suite path** companion for YTSDownloader with **on-device title resolve** (oEmbed, v0.8.0), **on-device yt-dlp download** (Chaquopy, v0.9.0 slice 2), **bundled ffmpeg merge** (v0.10.0 slice 3), **optional PNG watermark overlay** (v0.11.0 slice 4), and **multi-worker + SAF cookies + export presets** (v0.12.0 slice 5). Desktop Suite remains richest for deep crawl and cookies-from-browser profiles.

## What ships in this slice

| Capability | Status |
| --- | --- |
| Paste URL → local queue | Yes |
| Share sheet (`ACTION_SEND` text) → queue | Yes |
| On-device **title resolve** (YouTube oEmbed + noembed fallback) | Yes (v0.8.0) |
| Queue rows show title + URL | Yes (v0.8.0) |
| On-device **yt-dlp download** (Chaquopy Python 3.12) | Yes (v0.9.0) |
| Bundled **arm64 ffmpeg merge** (`bestvideo+bestaudio` → mp4) | Yes (v0.10.0); single-file fallback if asset/ABI missing |
| Optional **PNG watermark overlay** (full-frame stretch via bundled ffmpeg) | Yes (v0.11.0); preset `watermark` or ADB `--ez yts_watermark true` |
| **Multi-worker** concurrent downloads (bounded 1–4, default 2) | Yes (v0.12.0); spinner + ADB `--ei yts_max_workers N` |
| **Export presets** `audio_only` / `video_audio` / `watermark` | Yes (v0.12.0); spinner + ADB `--es yts_preset …` |
| **Cookies** Netscape `cookies.txt` via SAF (no Play Services) | Yes (v0.12.0); Pick cookies → app-private copy |
| Queue download status (queued / downloading / done / error) | Yes (v0.9.0) |
| Export JSON via Storage Access Framework (folder or create-document) | Yes |
| Export to Downloads / app files (no SAF chooser); optional `title` in payload | Yes |
| Share NDJSON / JSONL payload | Yes |
| Cookies-from-browser profiles / deep crawl | Desktop only |
| Google Play Services / FCM | None (ADB sideload only) |
| Cleartext HTTP | Off by default (`usesCleartextTraffic=false` + network security config) |

Payload shapes match [Architecture → Browser companion handoff](architecture.md#browser-companion-handoff-contract) (`schema: 1`, `url`, `source: android-companion`). Media files stay on-device under app-specific storage; inbox export remains the handoff for desktop Suite enqueue.

## Cookies on GrapheneOS (no Play Services)

On-device yt-dlp accepts a **Netscape `cookies.txt`** file only (same as desktop `COOKIES_FILE`). There is no cookies-from-browser path on phone/Quest.

1. On a desktop browser you trust, export cookies for the site (Netscape format) to `cookies.txt`.
2. Copy the file onto the phone (Files, USB, etc.).
3. In YTS Companion: **Pick cookies.txt (SAF)** → select the file. The app copies it into private storage (`files/cookies/cookies.txt`).
4. **Clear cookies** removes the app copy.

Do not commit cookie files. Private / age-gated media still needs a valid export; public smoke URLs work without cookies.

## Prerequisites

- JDK **17** (`JAVA_HOME`)
- Android SDK with **platform 36** (or 35) and **build-tools 35.x** already installed under `ANDROID_HOME`
- Host **Python 3.12** on `PATH` (or `CHAQUOPY_PYTHON`) — Chaquopy pip-installs yt-dlp at build time
- `adb` for install / smoke

## Build

From the repo root (fish-safe — invoke the script; do not `source` bash activate helpers):

```bash
./scripts/build_android.sh
```

Optional: `export CHAQUOPY_PYTHON=/path/to/python3.12` if `python3.12` is not discovered.

Debug APK path:

`android/app/build/outputs/apk/phone/debug/app-phone-debug.apk`

Application id (debug): `dev.voxhash.ytscompanion.debug`

First Chaquopy build downloads the Python runtime + `yt-dlp==2026.10.21` into the APK (tens of MB; arm64-v8a + x86_64). Build scripts also run `./scripts/fetch_android_ffmpeg.sh` to place a pinned LGPL arm64-v8a `ffmpeg` under `android/app/src/main/assets/ffmpeg/` (~16 MB; not committed — fetched at build time). Meta Quest 3 uses a separate flavor — see [quest.md](quest.md) / `./scripts/build_quest.sh` (same yt-dlp + ffmpeg stack).

## Install on GrapheneOS / Pixel (ADB sideload)

1. On the phone: **Settings → Developer options → USB debugging** (and authorize this computer when prompted).
2. Confirm the device:

```bash
adb devices -l
```

You want a line with `device` (not `unauthorized` / `offline`). Pixel 7 Pro typically shows `product:cheetah` / `model:Pixel_7_Pro`.

When several phones share the host, always target the Pixel serial (example: `29211FDH300NEB`):

```bash
adb -s 29211FDH300NEB install -r android/app/build/outputs/apk/phone/debug/app-phone-debug.apk
```

3. If **unauthorized**: unlock the phone, accept the RSA fingerprint dialog, run `adb kill-server && adb start-server && adb devices` again.
4. If **offline** / missing: try another cable/port, disable/enable USB debugging, or select **File transfer / Android Auto** USB mode. Confirm USB still sees the phone with `lsusb -d 18d1:` (Pixel vendor). If `lsusb` shows `Pixel 7 Pro` / `18d1:4ee7` but `adb devices` does not, other `adb` servers on non-default ports may own the USB node — see troubleshooting below.
5. Install (replace existing debug build):

```bash
adb install -r android/app/build/outputs/apk/phone/debug/app-phone-debug.apk
```

6. Launch:

```bash
adb shell am start -n dev.voxhash.ytscompanion.debug/dev.voxhash.ytscompanion.MainActivity
```

## Smoke e2e checklist

1. Open **YTS Companion**.
2. Paste an `https://` media page URL → **Add** (row appears in Local queue), **or** inject via ADB:

```bash
adb -s <pixel-serial> shell am start -n dev.voxhash.ytscompanion.debug/dev.voxhash.ytscompanion.MainActivity \
  -a android.intent.action.SEND -t 'text/plain' \
  --es android.intent.extra.TEXT 'https://www.youtube.com/watch?v=jNQXAC9IVRw'
```

3. Confirm queue prefs: `run-as` → `shared_prefs/yts_companion.xml` (`queue_urls`).
4. **On-device download** (v0.9.0+): tap **Download queue** / per-row **DL**, or ADB:

```bash
adb -s <pixel-serial> shell am start -n dev.voxhash.ytscompanion.debug/dev.voxhash.ytscompanion.MainActivity \
  -a dev.voxhash.ytscompanion.action.DOWNLOAD_QUEUE \
  --es yts_preset video_audio \
  --ei yts_max_workers 2

adb -s <pixel-serial> shell ls -la /sdcard/Android/data/dev.voxhash.ytscompanion.debug/files/Movies/YTSCompanion/
```

Helper: `./scripts/smoke_android_download.sh` (builds must already exist; prefers Pixel `29211FDH300NEB`, scans farm adb ports for `cheetah`).

- Watermark: `WATERMARK=1` or `PRESET=watermark ./scripts/smoke_android_download.sh`
- Audio only: `PRESET=audio_only ./scripts/smoke_android_download.sh`
- Workers: `MAX_WORKERS=3 ./scripts/smoke_android_download.sh`

**Device smoke (2026-10-24):** Pixel 7 Pro `29211FDH300NEB` / `cheetah` — install phone debug APK, SEND + `DOWNLOAD_QUEUE`, complete files under app `Movies/YTSCompanion/` (merge / preset / optional watermark), no `FATAL EXCEPTION`. If default `adb` (5037) is empty while `lsusb` shows the Pixel, reclaim farm ports or set `ANDROID_ADB_SERVER_PORT` (see troubleshooting).

5. Preferred ADB **inbox** handoff (no SAF / share chooser): **Export to Downloads** — MediaStore `Download/YTSCompanion/*.json` plus app-files copy under `Android/data/.../files/Download/`.

```bash
adb -s <pixel-serial> shell am start -n dev.voxhash.ytscompanion.debug/dev.voxhash.ytscompanion.MainActivity \
  -a dev.voxhash.ytscompanion.action.EXPORT_DOWNLOADS

adb -s <pixel-serial> shell ls -la /sdcard/Download/YTSCompanion/
adb -s <pixel-serial> pull /sdcard/Download/YTSCompanion/yts_companion_<stamp>.json .ytsdownloader/inbox/
```

Or tap **Export to Downloads** in the app. Equivalent extra: `--ez yts_export_downloads true`.

6. Optional on-device paths (verified on Pixel 7 Pro / Android 17 with **uiautomator2**; stock `adb shell uiautomator dump` often omits `ChooserActivity` / DocumentsUI details):
   - **Share payload** — opens system chooser with NDJSON/`text/plain`; Copy / Keep notes / Files targets work; Google “Save” rejects raw text.
   - **Choose export folder (SAF)** — pick `Download/YTSCompanion` (or another writable folder) → Allow → label shows `content://…/tree/…`; **Export inbox file** writes JSON into that tree.
   - **Create document** — with export folder unset, **Export inbox file** opens DocumentsUI SAVE; confirm into Downloads (or the last browsed folder) and `adb pull`.
   - **Pick cookies.txt (SAF)** — select a Netscape export; label shows the app-private copy name.
7. On desktop, drop the JSON into `.ytsdownloader/inbox/` (or append NDJSON to `companion_inbox.jsonl`) while the Suite is running — or verify with `consume_companion_inbox` / `parse_companion_payload` (`schema: 1`, `source: android-companion`).
8. Confirm the Suite enqueues the URL (same path as Link Grabber / drop zone).

Logcat (errors only):

```bash
adb logcat -d --pid="$(adb shell pidof -s dev.voxhash.ytscompanion.debug)" '*:E'
```

Also useful: `python.stderr` / `YtDlpBridge` tags when diagnosing on-device yt-dlp.

### Troubleshooting: Pixel in `lsusb` but not in `adb devices`

A USB farm with many phones often leaves **extra `adb` servers** listening on ports other than `5037`. One of those can open the Pixel’s `/dev/bus/usb/...` node while the default client still shows only other devices.

1. `lsusb -d 18d1:` — confirm `Pixel 7 Pro` / `18d1:4ee7` (charging + debug).
2. `fuser -v /dev/bus/usb/<bus>/<dev>` — see which `adb -L tcp:NNNN` holds the node.
3. `ANDROID_ADB_SERVER_PORT=NNNN adb devices -l` — list devices on that server (look for `product:cheetah`).
4. Or stop every server and reopen one clean listener: `pkill -x adb`; `usbreset 18d1:4ee7`; `adb start-server`; `adb devices -l`.

## Desktop handoff reminder

Inbox export still feeds the Suite queue. On-device yt-dlp (slices 2–5) writes media into app storage for local playback / pull (merge, presets, multi-worker, optional watermark, optional SAF cookies). Desktop remains richest for deep crawl and cookies-from-browser. See [architecture.md](architecture.md#local-inbox-protocol-v1).
