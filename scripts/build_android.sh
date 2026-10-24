#!/usr/bin/env bash
# Build the YTS Companion debug APK (GrapheneOS-friendly; no Play Services).
# Fish-safe: ./scripts/build_android.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ANDROID_DIR="$ROOT/android"

export ANDROID_HOME="${ANDROID_HOME:-/opt/android-sdk}"
export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$ANDROID_HOME}"

if [[ -z "${JAVA_HOME:-}" ]]; then
  if [[ -x "${HOME}/.local/jdk/jdk-17/bin/java" ]]; then
    export JAVA_HOME="${HOME}/.local/jdk/jdk-17"
  elif [[ -x "${HOME}/.local/jdk/jdk-17.0.21+9/bin/java" ]]; then
    export JAVA_HOME="${HOME}/.local/jdk/jdk-17.0.21+9"
  fi
fi
if [[ -n "${JAVA_HOME:-}" ]]; then
  export PATH="${JAVA_HOME}/bin:${PATH}"
fi

if [[ ! -d "$ANDROID_HOME" ]]; then
  echo "ANDROID_HOME not found ($ANDROID_HOME). Install Android SDK or export ANDROID_HOME." >&2
  exit 1
fi

if [[ ! -f "$ANDROID_DIR/local.properties" ]]; then
  printf 'sdk.dir=%s\n' "$ANDROID_HOME" >"$ANDROID_DIR/local.properties"
  echo "Wrote $ANDROID_DIR/local.properties"
fi

cd "$ANDROID_DIR"
if [[ ! -x ./gradlew ]]; then
  echo "Missing gradlew — generate with: gradle wrapper --gradle-version 8.11.1" >&2
  exit 1
fi

./gradlew :app:assemblePhoneDebug "$@"
APK="$ANDROID_DIR/app/build/outputs/apk/phone/debug/app-phone-debug.apk"
if [[ -f "$APK" ]]; then
  echo "APK: $APK"
else
  echo "Build finished but APK not found at $APK" >&2
  exit 1
fi
