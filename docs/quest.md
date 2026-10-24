# Meta Quest 3 companion (Horizon OS 2D panel)

Headset-side **browse/queue shell** for YTSDownloader. The desktop Suite remains the primary downloader; this panel collects media page URLs and exports companion-inbox payloads (`source: quest-companion`).

**Not** immersive OpenXR or Horizon Store packaging. On-device yt-dlp single-file download is shared with the phone flavor (v0.9.0); watermark / ffmpeg merge still later. Store policies and headset storage still constrain immersive packaging.

## What ships in this slice

| Capability | Status |
| --- | --- |
| Horizon OS **2D panel** APK (`quest` product flavor) | Yes |
| Paste URL → local queue | Yes |
| ADB `ACTION_SEND` / export-to-Downloads handoff | Yes |
| Larger landscape controls for controller / hand pointing | Yes |
| Inbox JSON `schema: 1` / `source: quest-companion` | Yes |
| Immersive VR / Spatial SDK | No |
| Horizon Store submission / VRC packaging | No |
| On-device media download | No (desktop Suite) |

Payload shapes match [Architecture → Browser companion handoff](architecture.md#browser-companion-handoff-contract).

## Prerequisites

- Same as [Android companion](android.md): JDK **17**, Android SDK (`compileSdk` 36 / build-tools 35.x), `adb`
- Meta Quest headset with **Developer Mode** on (Meta Horizon mobile app → Devices → Developer Mode)
- USB-C **data** cable (box charge-only cables will not enumerate ADB)

## Build

```bash
./scripts/build_quest.sh
```

Debug APK path:

`android/app/build/outputs/apk/quest/debug/app-quest-debug.apk`

Application id: `dev.voxhash.ytscompanion.quest` (stable across debug/release for Horizon panel + ADB)

Phone / GrapheneOS companion remains `./scripts/build_android.sh` → `…/phone/debug/app-phone-debug.apk`.

## Install on Quest 3 (ADB sideload)

1. Enable Developer Mode; put the headset on and accept **Allow USB debugging** when prompted.
2. Confirm the device:

```bash
adb devices -l
```

Quest 3 typically shows `product:eureka` / `model:Quest_3` (example serial `2G0YC5ZGB6031R`).

```bash
QUEST_SERIAL=2G0YC5ZGB6031R   # replace with your serial
adb -s "$QUEST_SERIAL" install -r android/app/build/outputs/apk/quest/debug/app-quest-debug.apk
```

3. Launch (Unknown Sources / Library, or ADB):

```bash
adb -s "$QUEST_SERIAL" shell am start -n \
  dev.voxhash.ytscompanion.quest/dev.voxhash.ytscompanion.quest.MainActivity
```

Sideloaded apps appear under **Library → Unknown Sources** on the headset.

**ADB cold-start note (Horizon OS):** after a fresh `adb install`, `am start -n …` (and `metavr app launch`) return **Error type 3** (`Activity class … does not exist` / no launchable activity) even though `dumpsys package` lists the activity and `com.oculus.intent.category.2D`. Horizon filters sideloaded apps from ActivityManager resolution until the first **Library → Unknown Sources** open.

Verified on Quest 3 `2G0YC5ZGB6031R` (2026-10-23):

| Step | Result |
| --- | --- |
| `adb` reclaim + wake | OK (`product:eureka`, wakefulness Awake) |
| `am broadcast …prox_close` (simulate worn) | OK (`sys.hmt.mounted=1`, `HEADSET_MOUNTED`) |
| VR passcode UI | Blocks automation until entered (uiautomator2 sees keypad; Store PIN / `content://com.oculus.rc` not available on this device) |
| Library / Unknown Sources via ADB / metavr / uiautomator | Not reachable — home is VR-composited (empty a11y tree; screencap shows Bubbles home only) |
| On-headset SEND/EXPORT | **Not** verified until one manual Unknown Sources launch |
| Pixel fallback with Quest APK | Proves binary + `quest-companion` parse/consume |

Manual once: unlock passcode if shown → wear headset → Meta button → **Library → Unknown Sources → YTS Quest Companion**. Then `SKIP_INSTALL=1 ./scripts/smoke_quest.sh`. The smoke script always checks install + 2D registration on the Quest; if cold start is blocked it falls back to Pixel.

## Smoke e2e checklist

1. Open **YTS Quest Companion** on the headset (2D panel).
2. Paste an `https://` media page URL → **Add**, **or** inject via ADB:

```bash
adb -s "$QUEST_SERIAL" shell am start -n \
  dev.voxhash.ytscompanion.quest/dev.voxhash.ytscompanion.quest.MainActivity \
  -a android.intent.action.SEND -t 'text/plain' \
  --es android.intent.extra.TEXT 'https://example.com/watch?v=quest-smoke'
```

3. Confirm queue prefs:

```bash
adb -s "$QUEST_SERIAL" shell run-as dev.voxhash.ytscompanion.quest \
  cat shared_prefs/yts_companion.xml
```

4. Export for desktop handoff (no SAF required):

```bash
adb -s "$QUEST_SERIAL" shell am start -n \
  dev.voxhash.ytscompanion.quest/dev.voxhash.ytscompanion.quest.MainActivity \
  -a dev.voxhash.ytscompanion.action.EXPORT_DOWNLOADS

adb -s "$QUEST_SERIAL" shell ls -la /sdcard/Download/YTSCompanion/
adb -s "$QUEST_SERIAL" pull /sdcard/Download/YTSCompanion/ .ytsdownloader/inbox/
```

Or: `./scripts/smoke_quest.sh` (detects `model:Quest_3` when present).

5. On desktop, `consume_companion_inbox` / `parse_companion_payload` should accept `schema: 1` / `source: quest-companion`.

Logcat:

```bash
adb -s "$QUEST_SERIAL" logcat -d \
  --pid="$(adb -s "$QUEST_SERIAL" shell pidof -s dev.voxhash.ytscompanion.quest)" '*:E'
```

## Desktop handoff reminder

Inbox export still feeds the desktop Suite. On-device yt-dlp (when the panel is open via Unknown Sources) writes media under app storage; desktop remains the richest watermark / merge path. See [architecture.md](architecture.md#local-inbox-protocol-v1).
