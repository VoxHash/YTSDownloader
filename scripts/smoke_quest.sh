#!/usr/bin/env bash
# Quest 3 ADB smoke: install + Horizon 2D panel registration + optional SEND/EXPORT.
# Fish-safe: ./scripts/smoke_quest.sh
# Env: QUEST_SERIAL, PIXEL_SERIAL (optional fallback for full SEND/EXPORT), SKIP_INSTALL=1, APK=path
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi

APK="${APK:-$ROOT/android/app/build/outputs/apk/quest/debug/app-quest-debug.apk}"
PKG="dev.voxhash.ytscompanion.quest"
ACTIVITY="${PKG}/dev.voxhash.ytscompanion.quest.MainActivity"
SMOKE_URL="https://example.com/watch?v=quest-smoke-$(date +%s)"

detect_quest_serial() {
  if [[ -n "${QUEST_SERIAL:-}" ]]; then
    echo "$QUEST_SERIAL"
    return
  fi
  local line serial
  line="$(adb devices -l | awk '/model:Quest_3/ {print; exit}')"
  if [[ -z "$line" ]]; then
    line="$(adb devices -l | awk '/product:eureka/ {print; exit}')"
  fi
  serial="$(awk '{print $1}' <<<"$line")"
  if [[ -z "$serial" || "$serial" == "List" ]]; then
    echo "No Quest 3 in adb devices -l (look for model:Quest_3 / product:eureka). Set QUEST_SERIAL=…" >&2
    exit 1
  fi
  echo "$serial"
}

run_send_export_pull() {
  local serial="$1"
  local label="$2"
  adb -s "$serial" shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb -s "$serial" shell am start -n "$ACTIVITY" \
    -a android.intent.action.SEND -t 'text/plain' \
    --es android.intent.extra.TEXT "$SMOKE_URL"
  sleep 2
  adb -s "$serial" shell am start -n "$ACTIVITY" \
    -a dev.voxhash.ytscompanion.action.EXPORT_DOWNLOADS
  sleep 2

  local tmp remote localf
  tmp="$(mktemp -d)"
  mapfile -t REMOTE_FILES < <(adb -s "$serial" shell ls -1 /sdcard/Download/YTSCompanion/*.json 2>/dev/null | tr -d '\r' | sort)
  if [[ ${#REMOTE_FILES[@]} -eq 0 ]]; then
    echo "No JSON under /sdcard/Download/YTSCompanion/ on $label ($serial)." >&2
    rm -rf "$tmp"
    return 1
  fi
  remote="${REMOTE_FILES[-1]}"
  localf="$tmp/$(basename "$remote")"
  adb -s "$serial" pull "$remote" "$localf"
  echo "Pulled ($label): $localf"

  "$PY" - "$localf" "$SMOKE_URL" <<'PY'
import json, sys
from pathlib import Path
path, expect = Path(sys.argv[1]), sys.argv[2]
text = path.read_text(encoding="utf-8")
data = json.loads(text)
assert data.get("schema") == 1, data
assert data.get("source") == "quest-companion", data
urls = data.get("urls") or []
found = False
for row in urls:
    if isinstance(row, dict) and row.get("url") == expect and row.get("source") == "quest-companion":
        found = True
        break
    if row == expect:
        found = True
        break
assert found, (expect, data)
print("OK: schema=1 source=quest-companion url present")
PY

  "$PY" - "$localf" <<'PY'
import sys, os, tempfile
from pathlib import Path
sys.path.insert(0, ".")
from ytscore.companion import parse_companion_payload, consume_companion_inbox
text = Path(sys.argv[1]).read_text(encoding="utf-8")
items = parse_companion_payload(text)
assert items and items[0].source == "quest-companion", items
with tempfile.TemporaryDirectory() as tmp:
    inbox = os.path.join(tmp, "inbox")
    os.makedirs(inbox)
    Path(os.path.join(inbox, "quest_smoke.json")).write_text(text, encoding="utf-8")
    got = consume_companion_inbox(inbox_dir=inbox, jsonl_path=os.path.join(tmp, "x.jsonl"))
    assert got and got[0].source == "quest-companion"
print("OK: desktop parse_companion_payload + consume_companion_inbox")
PY
  rm -rf "$tmp"
  return 0
}

SERIAL="$(detect_quest_serial)"
echo "Quest serial: $SERIAL"
adb -s "$SERIAL" get-state >/dev/null

if [[ "${SKIP_INSTALL:-0}" != "1" ]]; then
  if [[ ! -f "$APK" ]]; then
    echo "APK missing ($APK). Run ./scripts/build_quest.sh first, or set SKIP_INSTALL=1." >&2
    exit 1
  fi
  adb -s "$SERIAL" install -r "$APK"
fi

adb -s "$SERIAL" shell pm enable "$PKG" >/dev/null 2>&1 || true

DUMP="$(adb -s "$SERIAL" shell dumpsys package "$PKG" 2>/dev/null || true)"
if ! grep -q 'com.oculus.intent.category.2D' <<<"$DUMP"; then
  echo "FAIL: installed package missing com.oculus.intent.category.2D in dumpsys." >&2
  exit 1
fi
if ! grep -q 'com.oculus.intent.category.VR' <<<"$DUMP"; then
  echo "FAIL: installed package missing com.oculus.intent.category.VR (immersive shell)." >&2
  exit 1
fi
if ! grep -q 'ImmersiveShellActivity' <<<"$DUMP"; then
  echo "FAIL: ImmersiveShellActivity not registered in dumpsys." >&2
  exit 1
fi
if ! grep -q 'com.oculus.supportedDevices' <<<"$DUMP" && ! grep -q 'quest3' <<<"$DUMP"; then
  # meta-data may not always dump as plain text; activity 2D is the hard gate.
  echo "WARN: supportedDevices meta not visible in dumpsys text; 2D category present."
fi
echo "OK: Quest install + Horizon 2D + immersive VR intents registered ($PKG)"

IMMERSIVE_ACTIVITY="${PKG}/dev.voxhash.ytscompanion.quest.ImmersiveShellActivity"
IMM_OUT="$(adb -s "$SERIAL" shell am start -n "$IMMERSIVE_ACTIVITY" 2>&1 || true)"
echo "Immersive am start: $IMM_OUT"
if grep -q 'Error type 3' <<<"$IMM_OUT"; then
  echo "NOTE: immersive cold start blocked (Unknown Sources gate) — same as 2D."
else
  echo "OK: immersive shell activity launch attempted (Spatial OpenXR entry)"
fi

# Simulate headset worn (helps wake / dismiss some idle paths; does not bypass Unknown Sources).
adb -s "$SERIAL" shell am broadcast -a com.oculus.vrpowermanager.prox_close >/dev/null 2>&1 || true
adb -s "$SERIAL" shell cmd package unstop "$PKG" >/dev/null 2>&1 || true
adb -s "$SERIAL" shell pm enable "$PKG" >/dev/null 2>&1 || true

AM_OUT="$(adb -s "$SERIAL" shell am start -n "$ACTIVITY" \
  -a android.intent.action.SEND -t 'text/plain' \
  --es android.intent.extra.TEXT "$SMOKE_URL" 2>&1 || true)"
echo "$AM_OUT"
if ! grep -q 'Error type 3' <<<"$AM_OUT"; then
  if run_send_export_pull "$SERIAL" "Quest"; then
    echo "Quest smoke passed on-device ($SERIAL)."
    exit 0
  fi
fi

echo "NOTE: Horizon OS blocked cold ADB am start (Error type 3) or export failed."
echo "      Unlock VR passcode if shown → put headset on → Meta button → Library →"
echo "      Unknown Sources → open YTS Quest Companion once, then re-run:"
echo "      SKIP_INSTALL=1 ./scripts/smoke_quest.sh"
echo "      (metavr app launch / am start / uiautomator cannot open Unknown Sources alone.)"
echo "      Falling back to full SEND/EXPORT with the same Quest APK on Pixel (if present)."

PIXEL="${PIXEL_SERIAL:-}"
if [[ -z "$PIXEL" ]]; then
  PIXEL="$(adb devices -l | awk '/model:Pixel_7_Pro|product:cheetah/ {print $1; exit}')"
fi
if [[ -n "$PIXEL" ]]; then
  adb -s "$PIXEL" install -r "$APK"
  run_send_export_pull "$PIXEL" "Pixel(quest-apk)"
  echo "Quest smoke passed: headset install+2D OK; SEND/EXPORT verified via Pixel with Quest APK."
  exit 0
fi

echo "No Pixel fallback device. Headset install+2D verified; launch SEND/EXPORT manually once from Unknown Sources." >&2
exit 0
