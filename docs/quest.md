# Meta Quest 3 companion (Horizon OS 2D panel)

Headset-side **browse/queue shell** for YTSDownloader. The desktop Suite remains the primary downloader; this panel collects media page URLs and exports companion-inbox payloads (`source: quest-companion`).

**Not** immersive OpenXR or Horizon Store packaging. On-device yt-dlp + bundled ffmpeg merge + watermark + multi-worker / presets / SAF cookies are shared with the phone flavor (v0.9.0–v0.12.0). Store policies and headset storage still constrain immersive packaging.

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

**ADB cold-start note (Horizon OS):** after a fresh `adb install`, `am start -n …` (and `metavr app launch`) may return **Error type 3** until the first **Library → Unknown Sources** open. After that gate is cleared, cold `am start` / `monkey` / SEND / EXPORT work on-headset.

Verified on Quest 3 `2G0YC5ZGB6031R` (2026-10-24 on-headset smoke passed; farm ADB often on `ANDROID_ADB_SERVER_PORT=5137`):

| Step | Result |
| --- | --- |
| `adb` reclaim + wake | OK (`product:eureka`, wakefulness Awake). Device may appear on a farm ADB port while Pixel shares the same server. |
| Quest debug APK install | OK (`app-quest-debug.apk`); `dumpsys package` lists `MainActivity` + `com.oculus.intent.category.2D` |
| Cold `am start` / `monkey` / SEND / EXPORT | **OK** after Unknown Sources gate cleared (uiautomator shows `YTS Quest Companion` 2D panel; queue prefs + Downloads export verified) |
| `am broadcast …prox_close` | Completes; `sys.hmt.mounted` may stay `0` without privilege |
| VR passcode UI | Can block automation until entered when the headset is locked |
| Library / Unknown Sources via ADB / metavr / empty a11y | Still not automatable for the *first* open — Meta-button Library remains VR-composited |
| On-headset SEND/EXPORT | **Verified** — `SKIP_INSTALL=1 ./scripts/smoke_quest.sh` passed on-device 2026-10-24 |
| Pixel fallback with Quest APK | Still available if cold start is blocked again after reinstall |

Manual once after install/reinstall: unlock passcode if shown → wear headset → Meta button → **Library → Unknown Sources → YTS Quest Companion**. Then `ANDROID_ADB_SERVER_PORT=… SKIP_INSTALL=1 ./scripts/smoke_quest.sh`.

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

Inbox export still feeds the desktop Suite. On-device yt-dlp (when the panel is open via Unknown Sources) writes media under app storage with the same merge / preset / multi-worker / SAF-cookie path as the phone flavor; desktop remains richest for deep crawl / cookies-from-browser. See [architecture.md](architecture.md#local-inbox-protocol-v1).
