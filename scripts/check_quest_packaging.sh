#!/usr/bin/env bash
# Validate Quest companion APK against Horizon Store packaging readiness checks
# (VRC.Quest.Packaging.1 / .2 / .6 style). Does NOT claim Store certification.
# Fish-safe: ./scripts/check_quest_packaging.sh [apk]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APK="${1:-$ROOT/android/app/build/outputs/apk/quest/release/app-quest-release.apk}"
MANIFEST_SRC="$ROOT/android/app/src/quest/AndroidManifest.xml"
GRADLE="$ROOT/android/app/build.gradle.kts"

export ANDROID_HOME="${ANDROID_HOME:-/opt/android-sdk}"
export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$ANDROID_HOME}"

fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "OK: $*"; }

find_tool() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    command -v "$name"
    return
  fi
  # Prefer highest build-tools version that has the binary (no ls fancy formatting).
  local best="" cand
  for cand in "$ANDROID_HOME"/build-tools/*/ "$ANDROID_SDK_ROOT"/build-tools/*/; do
    if [[ -x "${cand}${name}" ]]; then
      best="${cand}${name}"
    fi
  done
  if [[ -n "$best" ]]; then
    echo "$best"
    return
  fi
  return 1
}

[[ -f "$MANIFEST_SRC" ]] || fail "missing quest manifest $MANIFEST_SRC"
[[ -f "$GRADLE" ]] || fail "missing $GRADLE"

# Source-level VRC.Quest.Packaging.1 markers (2D panel).
grep -q 'android:installLocation="auto"' "$MANIFEST_SRC" \
  || fail "manifest missing installLocation=auto"
grep -q 'android.hardware.vr.headtracking' "$MANIFEST_SRC" \
  || fail "manifest missing vr.headtracking feature"
grep -q 'android:required="false"' "$MANIFEST_SRC" \
  || fail "manifest headtracking must be required=false for 2D panel"
grep -q 'android:excludeFromRecents="true"' "$MANIFEST_SRC" \
  || fail "manifest MainActivity missing excludeFromRecents=true"
grep -q 'com.oculus.supportedDevices' "$MANIFEST_SRC" \
  || fail "manifest missing com.oculus.supportedDevices"
grep -q 'com.oculus.intent.category.2D' "$MANIFEST_SRC" \
  || fail "manifest missing com.oculus.intent.category.2D"
grep -q 'com.oculus.application_type' "$MANIFEST_SRC" \
  || fail "manifest missing com.oculus.application_type=panel"
ok "quest AndroidManifest.xml packaging markers"

# Flavor SDK floor / Store-oriented target.
grep -q 'minSdk = 29' "$GRADLE" || fail "quest flavor minSdk should be 29 (Store floor)"
grep -q 'targetSdk = 34' "$GRADLE" || fail "quest flavor targetSdk should be 34 (Store recommend)"
grep -q 'arm64-v8a' "$GRADLE" || fail "abiFilters must include arm64-v8a (Packaging.6)"
ok "quest flavor minSdk/targetSdk + 64-bit abiFilters"

if [[ ! -f "$APK" ]]; then
  echo "WARN: APK not built yet ($APK). Source checks passed; run:"
  echo "  RELEASE=1 ./scripts/build_quest.sh && ./scripts/check_quest_packaging.sh"
  exit 0
fi

# Size gate (VRC.Quest.Packaging.5: APK < 1 GB).
BYTES="$(wc -c <"$APK" | tr -d ' ')"
if [[ "$BYTES" -ge 1073741824 ]]; then
  fail "APK is ${BYTES} bytes (>= 1 GiB Packaging.5 limit)"
fi
ok "APK size ${BYTES} bytes (< 1 GiB)"

APKSIGNER="$(find_tool apksigner || true)"
AAPT2="$(find_tool aapt2 || true)"
AAPT="$(find_tool aapt || true)"

if [[ -n "$APKSIGNER" ]]; then
  "$APKSIGNER" verify --verbose "$APK" >/tmp/yts-quest-apksigner.txt 2>&1 \
    || { cat /tmp/yts-quest-apksigner.txt >&2; fail "apksigner verify failed"; }
  if ! grep -qiE 'Verified using v2|APK Signature Scheme v2' /tmp/yts-quest-apksigner.txt; then
    # Some apksigner versions only print "Verified" — accept if verify exit 0 and not v1-only.
    if grep -qi 'v1 scheme' /tmp/yts-quest-apksigner.txt && ! grep -qi 'v2' /tmp/yts-quest-apksigner.txt; then
      cat /tmp/yts-quest-apksigner.txt >&2
      fail "APK appears v1-only (need Signature Scheme v2)"
    fi
  fi
  ok "apksigner verify (v2+ expected for Packaging.2)"
else
  echo "WARN: apksigner not found; skip signature scheme check"
fi

BADGING=""
if [[ -n "$AAPT2" ]]; then
  BADGING="$("$AAPT2" dump badging "$APK" 2>/dev/null || true)"
elif [[ -n "$AAPT" ]]; then
  BADGING="$("$AAPT" dump badging "$APK" 2>/dev/null || true)"
fi

if [[ -n "$BADGING" ]]; then
  echo "$BADGING" | grep -q "name='dev.voxhash.ytscompanion.quest'" \
    || fail "badging package name mismatch"
  # aapt: sdkVersion:'29' — aapt2: minSdkVersion:'29'
  echo "$BADGING" | grep -qE "(minSdkVersion|sdkVersion):'(29|[3-9][0-9])'" \
    || fail "badging minSdkVersion below Store floor 29"
  echo "$BADGING" | grep -qE "targetSdkVersion:'(3[2-6]|37)'" \
    || fail "badging targetSdkVersion outside 2D Store range 32–37"
  echo "$BADGING" | grep -qE "native-code:.*'arm64-v8a'" \
    || fail "badging missing arm64-v8a native-code"
  if echo "$BADGING" | grep -qE "native-code:.*'armeabi-v7a'"; then
    fail "badging includes armeabi-v7a (Packaging.6 requires 64-bit)"
  fi
  ok "aapt badging: package + sdk + arm64-v8a"
else
  echo "WARN: aapt/aapt2 not found; skip badging checks"
fi

ok "Quest packaging readiness checks passed for $APK"
echo "NOTE: This is packaging readiness only — not Horizon Store certification or content review."
