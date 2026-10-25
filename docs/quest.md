# Meta Quest 3 companion (Horizon OS hybrid: 2D panel + immersive shell)

Headset-side **browse/queue shell** for YTSDownloader. The desktop Suite remains the primary downloader; this APK collects media page URLs and exports companion-inbox payloads (`source: quest-companion`).

On-device yt-dlp + bundled ffmpeg merge + watermark + multi-worker / presets / SAF cookies are shared with the phone flavor (v0.9.0–v0.12.0; slice 6 polish in v0.14.0). **v0.13.0** added Horizon Store **packaging readiness**. **v0.14.0** adds a first **immersive OpenXR / Meta Spatial SDK shell** (panel-in-world hosting the same companion UI). Full Store **certification** (2D or immersive) is still not done. Store policies and headset storage still constrain what can ship on the Store.

## What ships in this slice

| Capability | Status |
| --- | --- |
| Horizon OS **2D panel** APK (`quest` product flavor) | Yes |
| Paste URL → local queue | Yes |
| ADB `ACTION_SEND` / export-to-Downloads handoff | Yes |
| Larger landscape controls for controller / hand pointing | Yes |
| Inbox JSON `schema: 1` / `source: quest-companion` | Yes |
| Store **packaging readiness** (VRC.Packaging-aligned release) | Yes (v0.13.0+) |
| Immersive VR / Spatial / OpenXR shell (panel-in-world) | Yes (v0.14.0) — first shell, not Store immersive cert |
| Horizon Store **certification** / content review / Dashboard accept | No |
| On-device media download | Shared with phone (Unknown Sources); Store policy may reject download tooling |

Payload shapes match [Architecture → Browser companion handoff](architecture.md#browser-companion-handoff-contract).

## Immersive shell (v0.14.0)

Hybrid app (Meta Spatial SDK **0.14**):

| Entry | Activity | Intent category |
| --- | --- | --- |
| Default Library / Unknown Sources | `quest.MainActivity` | `com.oculus.intent.category.2D` + `LAUNCHER` |
| Immersive OpenXR | `quest.ImmersiveShellActivity` | `com.oculus.intent.category.VR` |

`ImmersiveShellActivity` extends Spatial `AppSystemActivity`, registers `VRFeature`, and creates a world-locked panel via `ActivityPanelRegistration` that hosts the same `MainActivity` companion UI (queue / download / export). From the 2D panel, tap **Enter immersive (Spatial panel)** or:

```bash
adb -s "$QUEST_SERIAL" shell am start -n \
  dev.voxhash.ytscompanion.quest/dev.voxhash.ytscompanion.quest.ImmersiveShellActivity
```

**Honesty:** this is a first immersive shell that launches in VR. It is **not** Horizon Store immersive certification, content review, or a claim that download tooling is Store-policy accepted.

## Prerequisites

- Same as [Android companion](android.md): JDK **17**, Android SDK (`compileSdk` 36 / build-tools 35.x), `adb`
- Meta Quest headset with **Developer Mode** on (Meta Horizon mobile app → Devices → Developer Mode)
- USB-C **data** cable (box charge-only cables will not enumerate ADB)

## Build

Debug (Unknown Sources sideload):

```bash
./scripts/build_quest.sh
```

Debug APK path:

`android/app/build/outputs/apk/quest/debug/app-quest-debug.apk`

Store-oriented **release** (packaging readiness; not certification):

```bash
RELEASE=1 ./scripts/build_quest.sh
# → android/app/build/outputs/apk/quest/release/app-quest-release.apk
# runs ./scripts/check_quest_packaging.sh automatically
```

Application id: `dev.voxhash.ytscompanion.quest` (stable across debug/release for Horizon panel + ADB).

Phone / GrapheneOS companion remains `./scripts/build_android.sh` → `…/phone/debug/app-phone-debug.apk`.

### Horizon Store packaging readiness (v0.13.0+)

Aligned with Meta’s published packaging guidance for panel apps, extended for hybrid immersive markers — local checks only:

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
| `minSdk` / `targetSdk` | Quest flavor **29** / **34** (Store recommend) |
| 64-bit only | `arm64-v8a` (+ `x86_64` host); no `armeabi-v7a` |
| Meta Spatial SDK | quest flavor deps `meta-spatial-sdk` / toolkit / vr **0.14.0** |
| APK Signature Scheme v2+ | Release `signingConfig` via AGP |
| APK size &lt; 1 GiB | `check_quest_packaging.sh` |
| Network security config | Shared main app (cleartext off) |

Validate without rebuilding:

```bash
./scripts/check_quest_packaging.sh
# or: ./scripts/check_quest_packaging.sh path/to/app-quest-release.apk
```

**Signing:** without `QUEST_STORE_KEYSTORE`, release builds sign with `~/.android/debug.keystore` (local smoke only). For Developer Dashboard upload, set:

- `QUEST_STORE_KEYSTORE` — path to your upload keystore
- `QUEST_STORE_STORE_PASSWORD`
- `QUEST_STORE_KEY_ALIAS` (default `upload`)
- `QUEST_STORE_KEY_PASSWORD`

**Honesty:** packaging readiness ≠ Store listing. Content / policy review (especially on-device download tooling), full VRC suites beyond packaging markers, and immersive Store **certification** are **not** claimed done.

## Install on Quest 3 (ADB sideload)

1. Enable Developer Mode; put the headset on and accept **Allow USB debugging** when prompted.
2. Confirm the device:

```bash
adb devices -l
```

Quest 3 typically shows `product:eureka` / `model:Quest_3` (example serial `2G0YC5ZGB6031R`). Farm ADB may use a non-default server port (`ANDROID_ADB_SERVER_PORT`).

```bash
QUEST_SERIAL=2G0YC5ZGB6031R   # replace with your serial
adb -s "$QUEST_SERIAL" install -r android/app/build/outputs/apk/quest/debug/app-quest-debug.apk
# or release: …/quest/release/app-quest-release.apk
```

3. Launch 2D panel (Unknown Sources / Library, or ADB):

```bash
adb -s "$QUEST_SERIAL" shell am start -n \
  dev.voxhash.ytscompanion.quest/dev.voxhash.ytscompanion.quest.MainActivity
```

4. Launch immersive shell:

```bash
adb -s "$QUEST_SERIAL" shell am start -n \
  dev.voxhash.ytscompanion.quest/dev.voxhash.ytscompanion.quest.ImmersiveShellActivity
```

Sideloaded apps appear under **Library → Unknown Sources** on the headset.

**ADB cold-start note (Horizon OS):** after a fresh `adb install`, `am start -n …` (and `metavr app launch`) may return **Error type 3** until the first **Library → Unknown Sources** open. After that gate is cleared, cold `am start` / `monkey` / SEND / EXPORT / immersive entry work on-headset.

Verified on Quest 3 `2G0YC5ZGB6031R` (farm ADB often on `ANDROID_ADB_SERVER_PORT=5137`):

| Step | Result |
| --- | --- |
| `adb` reclaim + wake | OK (`product:eureka`) |
| Quest debug APK install | OK; dumpsys lists 2D `MainActivity` + VR `ImmersiveShellActivity` |
| Cold `am start` / SEND / EXPORT | OK after Unknown Sources gate |
| Immersive `am start` | Attempted / OK after Unknown Sources gate |
| On-headset SEND/EXPORT | Use `SKIP_INSTALL=1 ./scripts/smoke_quest.sh` |

Manual once after install/reinstall: unlock passcode if shown → wear headset → Meta button → **Library → Unknown Sources → YTS Quest Companion**. Then `SKIP_INSTALL=1 ./scripts/smoke_quest.sh`. For immersive: open **Enter immersive** or ADB-start `ImmersiveShellActivity` while wearing the headset.

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

Or: `./scripts/smoke_quest.sh` (detects `model:Quest_3` when present; also checks VR / ImmersiveShellActivity registration).

5. On desktop, `consume_companion_inbox` / `parse_companion_payload` should accept `schema: 1` / `source: quest-companion`.

Logcat:

```bash
adb -s "$QUEST_SERIAL" logcat -d \
  --pid="$(adb -s "$QUEST_SERIAL" shell pidof -s dev.voxhash.ytscompanion.quest)" '*:E'
```

## Desktop handoff reminder

Inbox export still feeds the desktop Suite. On-device yt-dlp (when the panel is open via Unknown Sources) writes media under app storage with the same merge / preset / multi-worker / SAF-cookie / retry path as the phone flavor; desktop remains richest for deep crawl / cookies-from-browser. See [architecture.md](architecture.md#local-inbox-protocol-v1).
