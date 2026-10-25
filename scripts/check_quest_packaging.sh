#!/usr/bin/env bash
# Validate Quest companion APK against Horizon Store packaging readiness checks
# (VRC.Quest.Packaging.1 / .2 / .6 style) plus hybrid immersive markers.
# Does NOT claim Store certification (2D or immersive).
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

# Hybrid packaging markers: 2D panel + immersive VR entry.
grep -q 'android:installLocation="auto"' "$MANIFEST_SRC" \
  || fail "manifest missing installLocation=auto"
grep -q 'android.hardware.vr.headtracking' "$MANIFEST_SRC" \
  || fail "manifest missing vr.headtracking feature"
grep -q 'android:excludeFromRecents="true"' "$MANIFEST_SRC" \
  || fail "manifest MainActivity missing excludeFromRecents=true"
grep -q 'com.oculus.supportedDevices' "$MANIFEST_SRC" \
  || fail "manifest missing com.oculus.supportedDevices"
grep -q 'com.oculus.intent.category.2D' "$MANIFEST_SRC" \
  || fail "manifest missing com.oculus.intent.category.2D"
grep -q 'com.oculus.intent.category.VR' "$MANIFEST_SRC" \
  || fail "manifest missing com.oculus.intent.category.VR (immersive shell)"
grep -q 'ImmersiveShellActivity' "$MANIFEST_SRC" \
  || fail "manifest missing ImmersiveShellActivity"
grep -q 'libossdk.oculus.so' "$MANIFEST_SRC" \
  || fail "manifest missing libossdk.oculus.so native library"
grep -q 'uses-horizonos-sdk\|uses-metavr-sdk' "$MANIFEST_SRC" \
  || fail "manifest missing Horizon OS SDK version marker"
ok "quest AndroidManifest.xml hybrid packaging markers (2D + immersive)"

# Flavor SDK floor / Store-oriented target.
grep -q 'minSdk = 29' "$GRADLE" || fail "quest flavor minSdk should be 29 (Store floor)"
grep -q 'targetSdk = 34' "$GRADLE" || fail "quest flavor targetSdk should be 34 (Store recommend)"
grep -q 'arm64-v8a' "$GRADLE" || fail "abiFilters must include arm64-v8a (Packaging.6)"
grep -q 'meta-spatial-sdk' "$GRADLE" || fail "quest flavor should depend on Meta Spatial SDK"
ok "quest flavor minSdk/targetSdk + 64-bit + Spatial SDK"

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
  if ! "$APKSIGNER" verify --verbose "$APK" 2>&1 | tee /tmp/yts-quest-apksigner.txt | grep -qi 'Verified using v2 scheme'; then
    # Some apksigner versions print differently — accept any Verified line + v2/v3 in output.
    if grep -qi 'Verified' /tmp/yts-quest-apksigner.txt && \
       grep -Eqi 'v2|v3' /tmp/yts-quest-apksigner.txt; then
      ok "apksigner: APK Signature Scheme v2+"
    else
      fail "apksigner did not confirm v2+ signature"
    fi
  else
    ok "apksigner: APK Signature Scheme v2+"
  fi
else
  echo "WARN: apksigner not found — skip signature check"
fi

BADGING=""
if [[ -n "$AAPT2" ]]; then
  BADGING="$("$AAPT2" dump badging "$APK" 2>/dev/null || true)"
elif [[ -n "$AAPT" ]]; then
  BADGING="$("$AAPT" dump badging "$APK" 2>/dev/null || true)"
fi

if [[ -n "$BADGING" ]]; then
  echo "$BADGING" | grep -q "package: name='dev.voxhash.ytscompanion.quest'" \
    || fail "badging package id mismatch"
  echo "$BADGING" | grep -Eq "sdkVersion:'29'|minSdkVersion:'29'" \
    || fail "badging minSdk expected 29"
  echo "$BADGING" | grep -Eq "targetSdkVersion:'34'" \
    || fail "badging targetSdk expected 34"
  echo "$BADGING" | grep -q "native-code: 'arm64-v8a'" \
    || fail "badging missing arm64-v8a"
  ok "aapt badging: package / minSdk 29 / targetSdk 34 / arm64-v8a"
else
  echo "WARN: aapt/aapt2 not found — skip badging checks"
fi

ok "Quest packaging readiness checks passed (not Store certification)"
