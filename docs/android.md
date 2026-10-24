# Android companion (GrapheneOS-friendly)

Lightweight **URL companion** for YTSDownloader. The desktop Suite remains the primary downloader; this app collects media page URLs and exports companion-inbox payloads the Suite already understands.

**Not** full Suite feature parity (resolve, yt-dlp download, watermark, queue workers). That stays deferred under ROADMAP → Platforms.

## What ships in this slice

| Capability | Status |
| --- | --- |
| Paste URL → local queue | Yes |
| Share sheet (`ACTION_SEND` text) → queue | Yes |
| Export JSON via Storage Access Framework (folder or create-document) | Yes |
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

3. If **unauthorized**: unlock the phone, accept the RSA fingerprint dialog, run `adb kill-server && adb start-server && adb devices` again.
4. If **offline** / missing: try another cable/port, disable/enable USB debugging, or select **File transfer / Android Auto** USB mode.
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
2. Paste an `https://` media page URL → **Add** (row appears in Local queue).
3. Optional: **Choose export folder (SAF)** → pick a directory GrapheneOS allows.
4. **Export inbox file** or **Share payload** → copy the file onto the desktop machine.
5. On desktop, drop the JSON into `.ytsdownloader/inbox/` (or append NDJSON to `companion_inbox.jsonl`) while the Suite is running.
6. Confirm the Suite enqueues the URL (same path as Link Grabber / drop zone).

Logcat (errors only):

```bash
adb logcat -d --pid="$(adb shell pidof -s dev.voxhash.ytscompanion.debug)" '*:E'
```

## Desktop handoff reminder

Companions must not download media bytes. Write complete inbox files; the Suite polls and resolves with yt-dlp. See [architecture.md](architecture.md#local-inbox-protocol-v1).
