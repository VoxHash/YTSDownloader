# Meta Quest 3 companion (Horizon OS hybrid: 2D panel + immersive shell)

End-to-end guide for the Quest flavor (**v0.15.x**): install, use after install (2D vs immersive), then packaging notes. Desktop Suite remains the primary rich downloader; the headset collects URLs and can run the shared on-device yt-dlp stack under Unknown Sources. Handoff: [cross-platform.md](cross-platform.md).

| Item | Value |
| --- | --- |
| App name | **YTS Quest Companion** |
| Application id | `dev.voxhash.ytscompanion.quest` (debug and release) |
| 2D activity | `dev.voxhash.ytscompanion.quest.MainActivity` (`com.oculus.intent.category.2D`) |
| Immersive activity | `dev.voxhash.ytscompanion.quest.ImmersiveShellActivity` (`com.oculus.intent.category.VR`) |
| Debug APK | `android/app/build/outputs/apk/quest/debug/app-quest-debug.apk` |
| Release APK | `android/app/build/outputs/apk/quest/release/app-quest-release.apk` |
| Inbox `source` | `quest-companion` |
| Export (preferred) | `/sdcard/Download/YTSCompanion/*.json` |

## What ships (v0.15.x)

| Capability | Status |
| --- | --- |
| Horizon OS **2D panel** APK (`quest` product flavor) | Yes |
| Paste URL → local queue | Yes |
| ADB `ACTION_SEND` / **Export to Downloads** | Yes |
| Larger landscape controls for controller / hand pointing | Yes |
| Inbox JSON `schema: 1` / `source: quest-companion` | Yes |
| Store **packaging readiness** (VRC.Packaging-aligned release) | Yes (v0.13.0+) |
| Immersive VR / Spatial / OpenXR shell (panel-in-world) | Yes (v0.14.0) — first shell, **not** Store immersive cert |
| Shared on-device yt-dlp / ffmpeg / presets / workers / SAF cookies / notifications | Yes (same stack as phone) |
| Horizon Store **certification** / content review | No |

---

## 1. Install (Quest 3)

### Prerequisites

- Same Android host toolchain as [android.md](android.md): JDK **17**, SDK (`compileSdk` 36 / build-tools 35.x), `adb`
- Meta Quest headset with **Developer Mode** on (Meta Horizon mobile app → Devices → Developer Mode)
- USB-C **data** cable (charge-only cables will not enumerate ADB)

### Build

Debug (Unknown Sources sideload):

```bash
./scripts/build_quest.sh
# → android/app/build/outputs/apk/quest/debug/app-quest-debug.apk
```

Store-oriented release (packaging readiness; **not** certification):

```bash
RELEASE=1 ./scripts/build_quest.sh
# → android/app/build/outputs/apk/quest/release/app-quest-release.apk
# runs ./scripts/check_quest_packaging.sh automatically
```

Phone / GrapheneOS remains `./scripts/build_android.sh` → `…/phone/debug/app-phone-debug.apk`.

### ADB sideload

1. Enable Developer Mode; put the headset on and accept **Allow USB debugging** when prompted.
2. Confirm the device:

```bash
adb devices -l
```

Quest 3 typically shows `product:eureka` / `model:Quest_3` (example serial `2G0YC5ZGB6031R`). Farm ADB may use `ANDROID_ADB_SERVER_PORT` (often `5137` on the verified farm host).

```bash
QUEST_SERIAL=2G0YC5ZGB6031R   # replace with your serial
adb -s "$QUEST_SERIAL" install -r android/app/build/outputs/apk/quest/debug/app-quest-debug.apk
# or release: …/quest/release/app-quest-release.apk
```

3. Sideloaded apps appear under **Library → Unknown Sources** on the headset.

### Unknown Sources one-time open (required)

**ADB cold-start note (Horizon OS):** after a fresh `adb install`, `am start -n …` (and `metavr app launch`) may return **Error type 3** until the first **Library → Unknown Sources** open.

Manual once after each install/reinstall:

1. Unlock the headset passcode if shown → wear the headset.
2. Meta button → **Library → Unknown Sources → YTS Quest Companion**.
3. After that gate is cleared, cold `am start` / `monkey` / SEND / EXPORT / immersive entry work from ADB.

Then smoke without reinstall:

```bash
SKIP_INSTALL=1 ./scripts/smoke_quest.sh
```

### Launch 2D vs immersive

| Mode | How |
| --- | --- |
| **2D panel** (default Library / Unknown Sources) | Open the app from Library, or ADB `MainActivity` |
| **Immersive** (Spatial panel-in-world) | In the 2D UI tap **Enter immersive (Spatial panel)**, or ADB `ImmersiveShellActivity` |

```bash
# 2D panel
adb -s "$QUEST_SERIAL" shell am start -n \
  dev.voxhash.ytscompanion.quest/dev.voxhash.ytscompanion.quest.MainActivity

# Immersive OpenXR shell (wear the headset)
adb -s "$QUEST_SERIAL" shell am start -n \
  dev.voxhash.ytscompanion.quest/dev.voxhash.ytscompanion.quest.ImmersiveShellActivity
```

`ImmersiveShellActivity` hosts the **same** companion UI (queue / download / export) on a world-locked panel. This is a first immersive shell — **not** Horizon Store immersive certification or a claim that download tooling is Store-policy accepted.

---

## 2. Use after install

Controls match the phone companion (landscape / larger hit targets): paste field, **Add**, **Export preset**, **Workers**, cookies SAF, **Download queue**, exports, plus **Enter immersive (Spatial panel)** on Quest.

### Queue (paste or SEND)

1. Open **YTS Quest Companion** (2D panel recommended for first use).
2. Paste an `https://` media page URL → **Add**, **or** ADB:

```bash
adb -s "$QUEST_SERIAL" shell am start -n \
  dev.voxhash.ytscompanion.quest/dev.voxhash.ytscompanion.quest.MainActivity \
  -a android.intent.action.SEND -t 'text/plain' \
  --es android.intent.extra.TEXT 'https://www.youtube.com/watch?v=jNQXAC9IVRw'
```

3. Confirm queue prefs if debugging:

```bash
adb -s "$QUEST_SERIAL" shell run-as dev.voxhash.ytscompanion.quest \
  cat shared_prefs/yts_companion.xml
```

### Presets, workers, cookies, download

Same behavior as [android.md → Use after install](android.md#2-use-after-install):

- **Export preset**: Audio only / Video + audio / Watermark
- **Workers**: 1–4
- **Pick cookies.txt (SAF)** / **Clear cookies** (Netscape only; no cookies-from-browser on headset)
- **Download queue** / per-row **DL** / **Retry** — media under app storage when Unknown Sources path allows on-device yt-dlp
- Notifications: local channel (same as phone); Store policy may still reject download tooling for a Store listing

### Export for desktop

```bash
adb -s "$QUEST_SERIAL" shell am start -n \
  dev.voxhash.ytscompanion.quest/dev.voxhash.ytscompanion.quest.MainActivity \
  -a dev.voxhash.ytscompanion.action.EXPORT_DOWNLOADS

adb -s "$QUEST_SERIAL" shell ls -la /sdcard/Download/YTSCompanion/
adb -s "$QUEST_SERIAL" pull /sdcard/Download/YTSCompanion/ .ytsdownloader/inbox/
```

Or tap **Export to Downloads** in the panel. Suite consumption: [cross-platform.md](cross-platform.md) (`schema: 1`, `source: quest-companion`).

Full helper: `./scripts/smoke_quest.sh` (detects `model:Quest_3`; checks VR / ImmersiveShellActivity registration).

### Enter immersive

1. From the 2D panel, tap **Enter immersive (Spatial panel)**, **or** ADB-start `ImmersiveShellActivity` while wearing the headset.
2. Use the same queue / download / export controls on the Spatial panel.
3. Honesty: packaging + shell ≠ Store immersive certification.

Logcat:

```bash
adb -s "$QUEST_SERIAL" logcat -d \
  --pid="$(adb -s "$QUEST_SERIAL" shell pidof -s dev.voxhash.ytscompanion.quest)" '*:E'
```

Verified on Quest 3 `2G0YC5ZGB6031R` (`eureka`, often `ANDROID_ADB_SERVER_PORT=5137`): install OK; cold SEND/EXPORT/immersive OK **after** Unknown Sources gate.

---

## 3. Horizon Store packaging readiness (v0.13.0+)

Aligned with Meta’s published packaging guidance for panel apps, plus hybrid immersive markers — local checks only:

| Check | Implementation |
| --- | --- |
| `installLocation=auto` | Quest manifest |
| `vr.headtracking` | Quest manifest (`required=true` for immersive) |
| `excludeFromRecents=true` on 2D launcher | Quest `MainActivity` |
| `com.oculus.supportedDevices` | `quest2\|questpro\|quest3\|quest3s` |
| `com.oculus.intent.category.2D` + MAIN/LAUNCHER | Quest `MainActivity` |
| `com.oculus.intent.category.VR` | Quest `ImmersiveShellActivity` |
| Horizon OS SDK marker | `horizonos:uses-horizonos-sdk` |
| `libossdk.oculus.so` | Required native library for Spatial/OpenXR |
| `minSdk` / `targetSdk` | Quest flavor **29** / **34** |
| 64-bit only | `arm64-v8a` (+ `x86_64` host); no `armeabi-v7a` |
| Meta Spatial SDK | quest flavor deps **0.14.0** |
| APK Signature Scheme v2+ | Release `signingConfig` via AGP |
| APK size &lt; 1 GiB | `check_quest_packaging.sh` |

```bash
./scripts/check_quest_packaging.sh
# or: ./scripts/check_quest_packaging.sh path/to/app-quest-release.apk
```

**Signing:** without `QUEST_STORE_KEYSTORE`, release builds sign with `~/.android/debug.keystore` (local smoke only). For Developer Dashboard upload set `QUEST_STORE_KEYSTORE`, `QUEST_STORE_STORE_PASSWORD`, `QUEST_STORE_KEY_ALIAS` (default `upload`), `QUEST_STORE_KEY_PASSWORD`.

**Honesty:** packaging readiness ≠ Store listing. Content / policy review (especially on-device download tooling), full VRC suites beyond packaging markers, and immersive Store **certification** are **not** claimed done.
