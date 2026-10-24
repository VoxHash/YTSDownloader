#!/usr/bin/env bash
# Fetch pinned LGPL Android arm64-v8a ffmpeg into app assets (for yt-dlp merge).
# Fish-safe: ./scripts/fetch_android_ffmpeg.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT/android/app/src/main/assets/ffmpeg/arm64-v8a"
OUT_BIN="$OUT_DIR/ffmpeg"

# FFmpeg 8.1.1 Android aarch64 — built --disable-gpl --disable-nonfree (LGPL-2.1).
# Source tree: https://github.com/hzw1199/Android-FFmpeg-Prebuilt (tag/path ffmpeg-8.1.1/bin/ffmpeg)
URL="${ANDROID_FFMPEG_URL:-https://raw.githubusercontent.com/hzw1199/Android-FFmpeg-Prebuilt/main/ffmpeg-8.1.1/bin/ffmpeg}"
EXPECT_SHA256="${ANDROID_FFMPEG_SHA256:-480defd776199b5434008565974de5bf99822371c3cd9c1f130fda2c57de6439}"

mkdir -p "$OUT_DIR"

if [[ -f "$OUT_BIN" ]]; then
  GOT="$(sha256sum "$OUT_BIN" | awk '{print $1}')"
  if [[ "$GOT" == "$EXPECT_SHA256" ]]; then
    echo "Android ffmpeg already present: $OUT_BIN"
    exit 0
  fi
  echo "Checksum mismatch for existing binary — re-fetching…" >&2
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
echo "Downloading Android ffmpeg → $OUT_BIN"
curl -fsSL -o "$TMP" "$URL"
GOT="$(sha256sum "$TMP" | awk '{print $1}')"
if [[ "$GOT" != "$EXPECT_SHA256" ]]; then
  echo "SHA256 mismatch: got $GOT expected $EXPECT_SHA256" >&2
  exit 1
fi
install -m 0755 "$TMP" "$OUT_BIN"
echo "OK: $OUT_BIN ($GOT)"
