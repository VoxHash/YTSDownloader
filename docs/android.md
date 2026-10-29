# Android companion (GrapheneOS-friendly)

End-to-end guide for the phone flavor (**v0.15.x**): install, use after install, then optional build / smoke for developers. Desktop Suite remains richest for deep crawl and cookies-from-browser profiles. Cross-device handoff: [cross-platform.md](cross-platform.md).

| Item | Value |
| --- | --- |
| App name | **YTS Companion** |
| Debug application id | `dev.voxhash.ytscompanion.debug` |
| Main activity | `dev.voxhash.ytscompanion.MainActivity` |
| Debug APK | `android/app/build/outputs/apk/phone/debug/app-phone-debug.apk` |
| Inbox `source` | `android-companion` |
| Media (on-device) | `Android/data/dev.voxhash.ytscompanion.debug/files/Movies/YTSCompanion/` |
| Export (preferred) | `/sdcard/Download/YTSCompanion/*.json` |

## What ships (v0.15.x)

| Capability | Status |
| --- | --- |
| Paste URL → local queue | Yes |
| Share sheet (`ACTION_SEND` text) → queue | Yes |
| On-device **title resolve** (YouTube oEmbed + noembed fallback) | Yes (v0.8.0) |
| Queue rows show title + URL | Yes |
| On-device **yt-dlp download** (Chaquopy Python 3.12) | Yes (v0.9.0) |
| Bundled **arm64 ffmpeg merge** (`bestvideo*+bestaudio` → mp4) | Yes (v0.10.0); single-file fallback if asset/ABI missing |
| Optional **PNG watermark overlay** | Yes (v0.11.0); preset `watermark` or ADB `--ez yts_watermark true` |
| **Multi-worker** concurrent downloads (1–4, default 2) | Yes (v0.12.0) |
| **Export presets** `audio_only` / `video_audio` / `watermark` | Yes (v0.12.0) |
| **Cookies** Netscape `cookies.txt` via SAF (validated + domain summary) | Yes (v0.12.0–v0.15.0) |
| Outer **retry / exponential backoff** | Yes (v0.14.0) |
| Queue **resume** + per-row **Retry** | Yes (v0.14.0) |
| **Download notifications** (local channel `yts_downloads`) | Yes (v0.15.0); `POST_NOTIFICATIONS` on API 33+; no FCM |
| Export JSON / Share NDJSON / Export to Downloads | Yes |
| Cookies-from-browser profiles / deep crawl | Desktop only |
| Google Play Services / FCM | None (ADB sideload / Unknown Sources only) |
| Cleartext HTTP | Off by default |

---

## 1. Install (GrapheneOS / Pixel)

No Play Store listing. Prefer **ADB sideload** from a machine that built or received the APK. You can also copy the APK and use **Install unknown apps** once.

### Prerequisites (host)

- JDK **17** (`JAVA_HOME`) if you build locally
- Android SDK with **platform 36** (or 35) and **build-tools 35.x** (`ANDROID_HOME`)
- Host **Python 3.12** on `PATH` (or `CHAQUOPY_PYTHON`) for Chaquopy builds
- `adb` on `PATH`

### Build the phone APK (once)

From the repo root (fish-safe — do not `source` bash activate helpers):

```bash
./scripts/build_android.sh
```

Optional: `export CHAQUOPY_PYTHON=/path/to/python3.12` if `python3.12` is not discovered.

Output: `android/app/build/outputs/apk/phone/debug/app-phone-debug.apk`

### ADB sideload (recommended)

1. On the phone: **Settings → System → Developer options → USB debugging** (enable Developer options first via build-number taps if needed). Unlock and accept the RSA fingerprint when prompted.
2. On GrapheneOS, treat USB debugging as temporary attack surface: enable only while installing/debugging, then disable. Prefer a data-capable USB cable and **File transfer** USB mode when the OS asks.
3. Confirm the device:

```bash
adb devices -l
```

You want a line with `device` (not `unauthorized` / `offline`). Pixel 7 Pro typically shows `product:cheetah` / `model:Pixel_7_Pro`.

When several phones share the host, target the Pixel serial (example farm device `29211FDH300NEB`):

```bash
adb -s 29211FDH300NEB install -r android/app/build/outputs/apk/phone/debug/app-phone-debug.apk
```

Or with a single device:

```bash
adb install -r android/app/build/outputs/apk/phone/debug/app-phone-debug.apk
```

4. Launch:

```bash
adb shell am start -n dev.voxhash.ytscompanion.debug/dev.voxhash.ytscompanion.MainActivity
```

5. If **unauthorized**: unlock, accept the dialog, `adb kill-server && adb start-server && adb devices`. If **offline** / missing while `lsusb -d 18d1:` shows the Pixel, see [Troubleshooting](#troubleshooting-pixel-in-lsusb-but-not-in-adb-devices).

### Unknown Sources / Install unknown apps (no ADB)

Use when you copy the APK onto the phone (USB file transfer, Files, etc.) instead of `adb install`:

1. Copy `app-phone-debug.apk` to the phone (e.g. Downloads).
2. Open **Files** (or the prompt’s source app), tap the APK.
3. If blocked: **Settings → Apps → Special app access → Install unknown apps** → enable **Allow from this source** for **Files**, **Download Manager**, or the app named in the dialog (wording matches stock Android / GrapheneOS).
4. Confirm the system install dialog → open **YTS Companion**.
5. Revoke **Install unknown apps** for that source afterward if you only needed a one-shot install.

ADB install does **not** require the Install unknown apps toggle.

### GrapheneOS notes

- No Google Play Services / FCM — this companion never needs them.
- Work / Private Space: `adb install` targets the owner user by default; install into other profiles via APK copy inside that profile, not host ADB alone.
- Cookies-from-browser APIs do not exist on GrapheneOS/AOSP; use Netscape `cookies.txt` via SAF (below) or hand URLs to the desktop Suite.

---

## 2. Use after install

App label: **YTS Companion**. Main screen: URL field, **Add**, **Export preset**, **Workers**, watermark toggle, cookie row, action buttons, **Local queue**.

### Queue URLs

1. Paste an `https://` media page URL → **Add** (row appears under **Local queue**; title resolves via oEmbed when possible).
2. Or share a link into the app (`ACTION_SEND` text/plain) from the browser / another app.
3. Or inject via ADB:

```bash
adb -s <pixel-serial> shell am start -n dev.voxhash.ytscompanion.debug/dev.voxhash.ytscompanion.MainActivity \
  -a android.intent.action.SEND -t 'text/plain' \
  --es android.intent.extra.TEXT 'https://www.youtube.com/watch?v=jNQXAC9IVRw'
```

Per-row controls: **DL** (download one), **Retry** (error rows), **Remove**.

### Cookies (SAF Netscape)

On-device yt-dlp accepts a **Netscape `cookies.txt`** only (same idea as desktop `COOKIES_FILE`).

1. On a desktop browser you trust, export cookies for the site (Netscape format) to `cookies.txt` (Netscape header or tab-separated cookie rows).
2. Copy the file onto the phone (Files, USB, etc.).
3. Tap **Pick cookies.txt (SAF)** → select the file. Import is **validated**; failures show a concrete reason. Success copies into private storage and shows a **domain summary** (row count, unique domains, top domains × counts).
4. **Clear cookies** removes the app copy.

Do not commit cookie files. Public smoke URLs often work without cookies; private / age-gated media need a valid export.

### Presets and workers

| UI | Values |
| --- | --- |
| **Export preset** | **Audio only** (`audio_only`), **Video + audio** (`video_audio`, default), **Watermark** (`watermark`) |
| **Workers** | 1–4 concurrent downloads (default **2**) |
| **Watermark overlay (bundled PNG)** | Toggle maps to the watermark preset |

ADB extras when starting download:

```bash
adb -s <pixel-serial> shell am start -n dev.voxhash.ytscompanion.debug/dev.voxhash.ytscompanion.MainActivity \
  -a dev.voxhash.ytscompanion.action.DOWNLOAD_QUEUE \
  --es yts_preset video_audio \
  --ei yts_max_workers 2
```

- Watermark: `--ez yts_watermark true` or `--es yts_preset watermark`
- Audio: `--es yts_preset audio_only`

### Download (on-device)

1. Tap **Download queue** (all pending rows) or per-row **DL**.
2. On Android 13+, the first download may prompt for notifications — allow to see progress in the status bar; deny still downloads.
3. Status per row: Queued → Downloading N% → Downloaded / Error. Transient CDN / SSL / 429 failures get outer retries with backoff; after process death, queued/downloading rows **resume**.
4. Files under app-specific Movies:

```bash
adb -s <pixel-serial> shell ls -la /sdcard/Android/data/dev.voxhash.ytscompanion.debug/files/Movies/YTSCompanion/
```

Helper: `./scripts/smoke_android_download.sh` (APK must already exist; prefers Pixel `29211FDH300NEB`).

```bash
PRESET=audio_only MAX_WORKERS=3 ./scripts/smoke_android_download.sh
WATERMARK=1 ./scripts/smoke_android_download.sh
```

### Notifications

- Channel id `yts_downloads` (low importance): progress / done / error.
- Local only — no FCM / Play Services.
- Deny notification permission → downloads continue; status-bar posts are skipped.

### Export for desktop Suite

Preferred (no SAF chooser):

1. Tap **Export to Downloads** (or ADB):

```bash
adb -s <pixel-serial> shell am start -n dev.voxhash.ytscompanion.debug/dev.voxhash.ytscompanion.MainActivity \
  -a dev.voxhash.ytscompanion.action.EXPORT_DOWNLOADS

adb -s <pixel-serial> shell ls -la /sdcard/Download/YTSCompanion/
adb -s <pixel-serial> pull /sdcard/Download/YTSCompanion/yts_companion_<stamp>.json .ytsdownloader/inbox/
```

Equivalent extra: `--ez yts_export_downloads true`.

2. With Suite running, the inbox poll (~1.5 s) enqueues URLs — see [cross-platform.md](cross-platform.md).

Other export paths:

| Button | Behavior |
| --- | --- |
| **Share payload** | System chooser with NDJSON / `text/plain` |
| **Choose export folder (SAF)** then **Export inbox file** | Writes JSON into the picked tree |
| **Export inbox file** with no folder | DocumentsUI create-document SAVE |

Payload: `schema: 1`, `source: android-companion` (see architecture / cross-platform docs).

---

## 3. Build details (developers)

First Chaquopy build downloads the Python runtime + `yt-dlp==2026.10.21` into the APK (tens of MB; arm64-v8a + x86_64). Build scripts also run `./scripts/fetch_android_ffmpeg.sh` for a pinned LGPL arm64-v8a `ffmpeg` under `android/app/src/main/assets/ffmpeg/` (~16 MB; not committed). Meta Quest uses `./scripts/build_quest.sh` — [quest.md](quest.md).

Logcat (errors only):

```bash
adb logcat -d --pid="$(adb shell pidof -s dev.voxhash.ytscompanion.debug)" '*:E'
```

Useful tags: `python.stderr`, `YtDlpBridge`.

### Troubleshooting: Pixel in `lsusb` but not in `adb devices`

A USB farm often leaves **extra `adb` servers** on ports other than `5037`.

1. `lsusb -d 18d1:` — confirm Pixel / `18d1:4ee7`.
2. `fuser -v /dev/bus/usb/<bus>/<dev>` — see which `adb -L tcp:NNNN` holds the node.
3. `ANDROID_ADB_SERVER_PORT=NNNN adb devices -l` — list devices on that server (`product:cheetah`).
4. Or: `pkill -x adb`; `usbreset 18d1:4ee7`; `adb start-server`; `adb devices -l`.

**Device smoke (2026-10-24+):** Pixel 7 Pro `29211FDH300NEB` / `cheetah` — phone debug APK, SEND + `DOWNLOAD_QUEUE`, files under app `Movies/YTSCompanion/`, no `FATAL EXCEPTION`.
