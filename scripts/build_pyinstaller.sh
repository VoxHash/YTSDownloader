#!/usr/bin/env bash
# Freeze YTSDownloader (PyQt6 Suite) with PyInstaller onedir.
# Run on the target OS (Linux or macOS) — PyInstaller does not cross-compile.
# Fish-safe: invoke as ./scripts/build_pyinstaller.sh (no venv activate required).
# Optional: YTS_PYTHON=/path/to/python  (defaults to .venv/bin/python)
# Optional: SMOKE=1  — after freeze, run an offscreen launch smoke (needs Qt plugins).
# Optional: BUNDLE_NATIVES=auto|1|0 — copy native/bin/ next to the freeze when present
#   (auto=default: copy if repo native/bin/ is non-empty; 1=require; 0=skip).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -n "${YTS_PYTHON:-}" ]]; then
  PY="$YTS_PYTHON"
  if [[ ! -x "$PY" ]]; then
    if command -v "$PY" >/dev/null 2>&1; then
      PY="$(command -v "$PY")"
    else
      echo "error: YTS_PYTHON=$YTS_PYTHON is not executable and not on PATH" >&2
      exit 1
    fi
  fi
else
  PY="$ROOT/.venv/bin/python"
  if [[ ! -x "$PY" ]]; then
    echo "error: missing $PY — create the venv and install requirements.txt first" >&2
    echo "  or set YTS_PYTHON to an interpreter that already has requirements.txt installed" >&2
    exit 1
  fi
fi

if [[ ! -f "$ROOT/main.py" || ! -f "$ROOT/config.ini" || ! -d "$ROOT/themes" ]]; then
  echo "error: run from a complete checkout (main.py, config.ini, themes/)" >&2
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "warning: ffmpeg/ffprobe not on PATH — freeze may succeed, but download/mux needs them at runtime" >&2
fi

"$PY" -m pip install -U "pyinstaller>=6.11"
"$PY" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name YTSDownloader \
  --onedir \
  --paths "$ROOT" \
  --collect-all yt_dlp \
  --collect-all imageio_ffmpeg \
  --collect-all moviepy \
  --collect-submodules ytscore \
  --collect-submodules ytsgui \
  --hidden-import PIL \
  --add-data "$ROOT/themes:themes" \
  --add-data "$ROOT/assets:assets" \
  --add-data "$ROOT/config.ini:." \
  --icon "$ROOT/assets/icons/256x256/ytsdownloader.png" \
  --specpath "$ROOT/build" \
  --workpath "$ROOT/build/pyi" \
  --distpath "$ROOT/dist" \
  "$ROOT/main.py"

OUT="$ROOT/dist/YTSDownloader"
# Suite reads config.ini / themes/ / assets from process cwd (not only from _internal datas).
cp -a "$ROOT/config.ini" "$OUT/config.ini"
rm -rf "$OUT/themes"
cp -a "$ROOT/themes" "$OUT/themes"
rm -rf "$OUT/assets"
cp -a "$ROOT/assets" "$OUT/assets"

# Optional native sidecars: ship as <onedir>/native/bin/ (Suite discovers via native_bridge).
SRC_NATIVE="$ROOT/native/bin"
BUNDLE_MODE="${BUNDLE_NATIVES:-auto}"
if [[ "$BUNDLE_MODE" != "0" ]]; then
  if [[ -d "$SRC_NATIVE" ]] && [[ -n "$(find "$SRC_NATIVE" -mindepth 1 -maxdepth 1 2>/dev/null | head -n 1)" ]]; then
    rm -rf "$OUT/native"
    mkdir -p "$OUT/native"
    cp -a "$SRC_NATIVE" "$OUT/native/bin"
    echo "Bundled native/bin/ → $OUT/native/bin/"
  elif [[ "$BUNDLE_MODE" == "1" ]]; then
    echo "warning: BUNDLE_NATIVES=1 but $SRC_NATIVE is empty — run ./scripts/build_natives.sh first" >&2
  else
    echo "Note: no native/bin/ to bundle (Python fallbacks). Build with ./scripts/build_natives.sh then re-freeze, or set BUNDLE_NATIVES=0 to silence."
  fi
fi

echo
echo "Built: $OUT/"
echo "Ship the entire folder. Runtime still needs ffmpeg and ffprobe on PATH."
echo "Optional natives live under native/bin/ next to the binary when bundled."
echo "Try:  cd dist/YTSDownloader && ./YTSDownloader"

if [[ "${SMOKE:-0}" == "1" ]]; then
  echo
  echo "SMOKE=1: offscreen launch (8s timeout)…"
  (
    cd "$OUT"
    # Windowed freezes still accept QT_QPA_PLATFORM for a brief start smoke.
    QT_QPA_PLATFORM=offscreen timeout 8 ./YTSDownloader || true
  )
  echo "Smoke finished (timeout/exit expected; binary must exist and start)."
  test -x "$OUT/YTSDownloader"
fi
