#!/usr/bin/env bash
# Isolated launcher for YTSDownloader (Linux desktop / PATH).
# Starts in a new session so sibling Qt apps sharing a launcher process group
# do not take this process down on close, and clears host Qt plugin vars that
# can couple multiple PyQt apps to one plugin host / chrome strip.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

# Do not inherit another Qt app's plugin / QML host paths.
unset QT_PLUGIN_PATH \
      QT_QPA_PLATFORM_PLUGIN_PATH \
      QTWEBENGINEPROCESS_PATH \
      QML2_IMPORT_PATH \
      QML_IMPORT_PATH \
      PYTHONPATH

PY="$ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "Missing venv python: $PY (run ./scripts/install_local.sh)" >&2
  exit 1
fi

# New session (preferred) so we are not in a sibling's process group.
if command -v setsid >/dev/null 2>&1; then
  exec setsid "$PY" "$ROOT/main.py" "$@"
fi

# Fallback: new process group under job control.
set -m
exec "$PY" "$ROOT/main.py" "$@"
