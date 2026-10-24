# Android companion (GrapheneOS-friendly)

Lightweight **URL companion** for YTSDownloader. The desktop Suite remains the primary downloader; this app collects media page URLs and exports companion-inbox payloads the Suite already understands.

**Not** full Suite feature parity (resolve, yt-dlp download, watermark, queue workers). That stays deferred under ROADMAP → Platforms.

## What ships in this slice

| Capability | Status |
| --- | --- |
| Paste URL → local queue | Yes |
| Share sheet (`ACTION_SEND` text) → queue | Yes |
| Export JSON via Storage Access Framework (folder or create-document) | Yes |
| Export to Downloads / app files (no SAF chooser) | Yes |
| Share NDJSON / JSONL payload | Yes |
| On-device download / extract | No (desktop Suite) |
| Google Play Services / FCM | None (ADB sideload only) |
| Cleartext HTTP | Off by default (`usesCleartextTraffic=false` + network security config) |

Payload shapes match [Architecture → Browser companion handoff](architecture.md#browser-companion-handoff-contract) (`schema: 1`, `url`, `source: android-companion`).

## Prerequisites

- JDK **17** (`JAVA_HOME`)
- Android SDK with **platform 36** (or 35) and **build-tools 35.x** already installed under `ANDROID_HOME` (the scaffold targets compileSdk 36 / build-tools 35.0.0 so it does not need a writable SDK to download packages)
- `adb` for install / smoke

## Build

From the repo root (fish-safe — invoke the script; do not `source` bash activate helpers):

```bash
./scripts/build_android.sh
```

Debug APK path:

`android/app/build/outputs/apk/debug/app-debug.apk`

Application id (debug): `dev.voxhash.ytscompanion.debug`

## Install on GrapheneOS / Pixel (ADB sideload)

1. On the phone: **Settings → Developer options → USB debugging** (and authorize this computer when prompted).
2. Confirm the device:

```bash
adb devices -l
```

You want a line with `device` (not `unauthorized` / `offline`). Pixel 7 Pro typically shows `product:cheetah` / `model:Pixel_7_Pro`.

When several phones share the host, always target the Pixel serial (example: `29211FDH300NEB`):

```bash
adb -s 29211FDH300NEB install -r android/app/build/outputs/apk/debug/app-debug.apk
```

3. If **unauthorized**: unlock the phone, accept the RSA fingerprint dialog, run `adb kill-server && adb start-server && adb devices` again.
4. If **offline** / missing: try another cable/port, disable/enable USB debugging, or select **File transfer / Android Auto** USB mode. Confirm USB still sees the phone with `lsusb -d 18d1:` (Pixel vendor). If `lsusb` shows `Pixel 7 Pro` / `18d1:4ee7` but `adb devices` does not, other `adb` servers on non-default ports may own the USB node — see troubleshooting below.
5. Install (replace existing debug build):

```bash
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
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
  --es android.intent.extra.TEXT 'https://example.com/watch?v=test'
```

3. Confirm queue prefs: `run-as` → `shared_prefs/yts_companion.xml` (`queue_urls`).
4. Preferred ADB handoff (no SAF / share chooser): **Export to Downloads** — MediaStore `Download/YTSCompanion/*.json` plus app-files copy under `Android/data/.../files/Download/`.

```bash
adb -s <pixel-serial> shell am start -n dev.voxhash.ytscompanion.debug/dev.voxhash.ytscompanion.MainActivity \
  -a dev.voxhash.ytscompanion.action.EXPORT_DOWNLOADS

adb -s <pixel-serial> shell ls -la /sdcard/Download/YTSCompanion/
adb -s <pixel-serial> pull /sdcard/Download/YTSCompanion/yts_companion_<stamp>.json .ytsdownloader/inbox/
```

Or tap **Export to Downloads** in the app. Equivalent extra: `--ez yts_export_downloads true`.

5. Optional on-device paths (verified on Pixel 7 Pro / Android 17 with **uiautomator2**; stock `adb shell uiautomator dump` often omits `ChooserActivity` / DocumentsUI details):
   - **Share payload** — opens system chooser with NDJSON/`text/plain`; Copy / Keep notes / Files targets work; Google “Save” rejects raw text.
   - **Choose export folder (SAF)** — pick `Download/YTSCompanion` (or another writable folder) → Allow → label shows `content://…/tree/…`; **Export inbox file** writes JSON into that tree.
   - **Create document** — with export folder unset, **Export inbox file** opens DocumentsUI SAVE; confirm into Downloads (or the last browsed folder) and `adb pull`.
6. On desktop, drop the JSON into `.ytsdownloader/inbox/` (or append NDJSON to `companion_inbox.jsonl`) while the Suite is running — or verify with `consume_companion_inbox` / `parse_companion_payload` (`schema: 1`, `source: android-companion`).
7. Confirm the Suite enqueues the URL (same path as Link Grabber / drop zone).

Logcat (errors only):

```bash
adb logcat -d --pid="$(adb shell pidof -s dev.voxhash.ytscompanion.debug)" '*:E'
```

### Troubleshooting: Pixel in `lsusb` but not in `adb devices`

A USB farm with many phones often leaves **extra `adb` servers** listening on ports other than `5037`. One of those can open the Pixel’s `/dev/bus/usb/...` node while the default client still shows only other devices.

1. `lsusb -d 18d1:` — confirm `Pixel 7 Pro` / `18d1:4ee7` (charging + debug).
2. `fuser -v /dev/bus/usb/<bus>/<dev>` — see which `adb -L tcp:NNNN` holds the node.
3. `ANDROID_ADB_SERVER_PORT=NNNN adb devices -l` — list devices on that server (look for `product:cheetah`).
4. Or stop every server and reopen one clean listener: `pkill -x adb`; `usbreset 18d1:4ee7`; `adb start-server`; `adb devices -l`.

## Desktop handoff reminder

Companions must not download media bytes. Write complete inbox files; the Suite polls and resolves with yt-dlp. See [architecture.md](architecture.md#local-inbox-protocol-v1).
