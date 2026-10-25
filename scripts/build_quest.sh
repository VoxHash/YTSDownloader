#!/usr/bin/env bash
# Build the YTS Quest Companion APK (Horizon OS 2D panel).
# Debug (default): Unknown Sources sideload.
# RELEASE=1: Store-oriented release APK (signed; packaging readiness, not Store cert).
# Fish-safe: ./scripts/build_quest.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ANDROID_DIR="$ROOT/android"
RELEASE="${RELEASE:-0}"

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

# Bundled arm64 ffmpeg for yt-dlp merge (slice 3); skipped if already hashed.
"$ROOT/scripts/fetch_android_ffmpeg.sh"

cd "$ANDROID_DIR"
if [[ ! -x ./gradlew ]]; then
  echo "Missing gradlew — generate with: gradle wrapper --gradle-version 8.11.1" >&2
  exit 1
fi

if [[ "$RELEASE" == "1" ]]; then
  if [[ -z "${QUEST_STORE_KEYSTORE:-}" ]]; then
    echo "NOTE: QUEST_STORE_KEYSTORE unset — signing with ~/.android/debug.keystore (local smoke only)."
    echo "      For Dashboard upload, set QUEST_STORE_KEYSTORE / QUEST_STORE_STORE_PASSWORD /"
    echo "      QUEST_STORE_KEY_ALIAS / QUEST_STORE_KEY_PASSWORD to your Meta upload cert."
  fi
  ./gradlew :app:assembleQuestRelease "$@"
  APK="$ANDROID_DIR/app/build/outputs/apk/quest/release/app-quest-release.apk"
else
  ./gradlew :app:assembleQuestDebug "$@"
  APK="$ANDROID_DIR/app/build/outputs/apk/quest/debug/app-quest-debug.apk"
fi

if [[ -f "$APK" ]]; then
  echo "APK: $APK"
  if [[ "$RELEASE" == "1" ]]; then
    "$ROOT/scripts/check_quest_packaging.sh" "$APK"
  fi
else
  echo "Build finished but APK not found at $APK" >&2
  exit 1
fi
