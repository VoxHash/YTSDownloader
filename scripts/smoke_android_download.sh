#!/usr/bin/env bash
# ADB smoke: install phone APK, enqueue a URL, trigger on-device yt-dlp download.
# Fish-safe: ./scripts/smoke_android_download.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APK="${APK:-$ROOT/android/app/build/outputs/apk/phone/debug/app-phone-debug.apk}"
PKG="${PKG:-dev.voxhash.ytscompanion.debug}"
ACTIVITY="$PKG/dev.voxhash.ytscompanion.MainActivity"
SERIAL="${ANDROID_SERIAL:-29211FDH300NEB}"
SMOKE_URL="${SMOKE_URL:-https://www.youtube.com/watch?v=jNQXAC9IVRw}"

if [[ ! -f "$APK" ]]; then
  echo "Missing APK: $APK — run ./scripts/build_android.sh first" >&2
  exit 1
fi

# Prefer the requested Pixel serial; fall back to first device on default adb.
if ! adb -s "$SERIAL" get-state >/dev/null 2>&1; then
  echo "Serial $SERIAL not on default adb — scanning farm ports for Pixel/cheetah…"
  FOUND=""
  for p in 5037 $(ss -ltn 2>/dev/null | awk '/127\.0\.0\.1:5[0-9]+/ {split($4,a,":"); print a[2]}' | sort -u); do
    mapfile -t lines < <(ANDROID_ADB_SERVER_PORT="$p" adb devices -l 2>/dev/null | awk '/device / && !/List/ {print}')
    for line in "${lines[@]:-}"; do
      if grep -Eq 'product:cheetah|model:Pixel_7_Pro|29211FDH300NEB' <<<"$line"; then
        FOUND="$(awk '{print $1}' <<<"$line")"
        export ANDROID_ADB_SERVER_PORT="$p"
        SERIAL="$FOUND"
        echo "Using Pixel $SERIAL on ANDROID_ADB_SERVER_PORT=$p"
        break 2
      fi
    done
  done
  if [[ -z "$FOUND" ]]; then
    # Last resort: any authorized device (e.g. Quest) for install-only smoke.
    SERIAL="$(adb devices | awk '/device$/ {print $1; exit}')"
    if [[ -z "$SERIAL" ]]; then
      echo "No adb device available for smoke." >&2
      exit 1
    fi
    echo "NOTE: Pixel not found; using $SERIAL"
  fi
fi

echo "Installing $APK → $SERIAL"
adb -s "$SERIAL" install -r "$APK"

WATERMARK="${WATERMARK:-0}"

adb -s "$SERIAL" shell am force-stop "$PKG" >/dev/null 2>&1 || true
# Fresh queue + media so DONE rows from prior smokes do not skip DOWNLOAD_QUEUE.
adb -s "$SERIAL" shell pm clear "$PKG" >/dev/null 2>&1 || true
adb -s "$SERIAL" shell "rm -rf /sdcard/Android/data/$PKG/files/Movies/YTSCompanion" >/dev/null 2>&1 || true

WM_EZ="false"
if [[ "$WATERMARK" = "1" ]]; then
  WM_EZ="true"
fi

adb -s "$SERIAL" shell am start -n "$ACTIVITY" \
  -a android.intent.action.SEND -t 'text/plain' \
  --es android.intent.extra.TEXT "$SMOKE_URL" \
  --ez yts_watermark "$WM_EZ"

sleep 3
adb -s "$SERIAL" shell am start -n "$ACTIVITY" \
  -a dev.voxhash.ytscompanion.action.DOWNLOAD_QUEUE \
  --ez yts_watermark "$WM_EZ"

echo "Waiting for on-device download (up to 240s)… watermark=$WATERMARK"
MEDIA_DIR="/sdcard/Android/data/$PKG/files/Movies/YTSCompanion"
OK=0
for _ in $(seq 1 48); do
  sleep 5
  COUNT="$(adb -s "$SERIAL" shell "ls -1 '$MEDIA_DIR' 2>/dev/null | wc -l" | tr -d '[:space:]')"
  PREFS="$(adb -s "$SERIAL" shell run-as "$PKG" cat shared_prefs/yts_companion.xml 2>/dev/null || true)"
  WM_FILES="$(adb -s "$SERIAL" shell "ls -1 '$MEDIA_DIR'/*_wm.* 2>/dev/null" | tr -d '\r' || true)"

  if [[ "$WATERMARK" = "1" ]]; then
    if [[ -n "$WM_FILES" ]] || grep -q '_wm\.' <<<"$PREFS"; then
      echo "OK: watermarked output present"
      adb -s "$SERIAL" shell ls -la "$MEDIA_DIR" || true
      OK=1
      break
    fi
    if grep -q 'ERROR' <<<"$PREFS"; then
      echo "FAIL: download/watermark ERROR in prefs" >&2
      echo "$PREFS" >&2
      adb -s "$SERIAL" logcat -d -t 80 -s python.stderr:I YtDlpBridge:E AndroidRuntime:E || true
      exit 1
    fi
  else
    if [[ "${COUNT:-0}" =~ ^[1-9] ]]; then
      echo "OK: media files in $MEDIA_DIR ($COUNT)"
      adb -s "$SERIAL" shell ls -la "$MEDIA_DIR" || true
      OK=1
      break
    fi
    if grep -q 'DONE' <<<"$PREFS"; then
      echo "OK: queue prefs show DONE"
      OK=1
      break
    fi
  fi
  echo "  …still waiting (files=$COUNT)"
done

if [[ "$OK" -ne 1 ]]; then
  echo "FAIL: no downloaded media after timeout" >&2
  adb -s "$SERIAL" logcat -d -t 80 -s python.stderr:I YtDlpBridge:E AndroidRuntime:E || true
  exit 1
fi

echo "Android download smoke passed ($SERIAL)."
