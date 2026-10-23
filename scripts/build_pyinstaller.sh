#!/usr/bin/env bash
# Freeze YTSDownloader (PyQt6 Suite) with PyInstaller onedir.
# Run on the target OS — PyInstaller does not cross-compile.
# Fish-safe: invoke as ./scripts/build_pyinstaller.sh (no venv activate required).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "error: missing $PY — create the venv and install requirements.txt first" >&2
  exit 1
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
  --add-data "$ROOT/config.ini:." \
  --specpath "$ROOT/build" \
  --workpath "$ROOT/build/pyi" \
  --distpath "$ROOT/dist" \
  "$ROOT/main.py"

OUT="$ROOT/dist/YTSDownloader"
# Suite reads config.ini / themes/ from process cwd (not only from _internal datas).
cp -a "$ROOT/config.ini" "$OUT/config.ini"
rm -rf "$OUT/themes"
cp -a "$ROOT/themes" "$OUT/themes"

echo
echo "Built: $OUT/"
echo "Ship the entire folder. Runtime still needs ffmpeg and ffprobe on PATH."
echo "Try:  cd dist/YTSDownloader && ./YTSDownloader"
