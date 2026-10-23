#!/usr/bin/env bash
# Install a single user-local launcher for this repo (dev install).
# Fish-safe: never sources activate scripts; uses .venv/bin/python only.
# Does not register dist/ freeze binaries — keep one source of truth.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
WRAPPER="$BIN_DIR/ytsdownloader"
DESKTOP="$APP_DIR/ytsdownloader.desktop"
PY="$ROOT/.venv/bin/python"

echo "==> Project: $ROOT"

if [[ ! -x "$PY" ]]; then
  echo "==> Creating .venv"
  python3 -m venv "$ROOT/.venv"
  PY="$ROOT/.venv/bin/python"
fi

echo "==> Ensuring dependencies"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r "$ROOT/requirements.txt"

mkdir -p "$BIN_DIR" "$APP_DIR"

# Drop competing user-local names so PATH / menus resolve to one entry.
for name in ytsdownloader YTSDownloader yts-downloader; do
  for dir in "$BIN_DIR" /usr/local/bin; do
    target="$dir/$name"
    if [[ -e "$target" || -L "$target" ]]; then
      if [[ "$target" == "$WRAPPER" ]]; then
        continue
      fi
      # Only remove under ~/.local without sudo; warn on /usr/local.
      if [[ "$dir" == "$BIN_DIR" ]]; then
        echo "==> Removing duplicate: $target"
        rm -f "$target"
      else
        echo "==> Skipping system path (not ours to delete without sudo): $target"
      fi
    fi
  done
done

for desk in "$APP_DIR"/ytsdownloader.desktop "$APP_DIR"/YTSDownloader.desktop \
            "$APP_DIR"/*ytsdownloader*.desktop "$APP_DIR"/*YTSDownloader*.desktop; do
  [[ -e "$desk" ]] || continue
  if [[ "$desk" != "$DESKTOP" ]]; then
    echo "==> Removing duplicate desktop entry: $desk"
    rm -f "$desk"
  fi
done

echo "==> Writing $WRAPPER"
cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
# Single machine install: YTSDownloader (project venv)
ROOT="$ROOT"
cd "\$ROOT" || exit 1
unset PYTHONPATH
exec "\$ROOT/.venv/bin/python" "\$ROOT/main.py" "\$@"
EOF
chmod +x "$WRAPPER"

echo "==> Writing $DESKTOP"
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Version=1.5
Name=YTSDownloader
GenericName=Download Suite
Comment=Multi-platform video/audio download suite (PyQt6)
Exec=$WRAPPER
Path=$ROOT
Terminal=false
Categories=AudioVideo;Network;
StartupNotify=true
StartupWMClass=YTSDownloader
EOF
chmod 644 "$DESKTOP"

if command -v update-desktop-database >/dev/null 2>&1; then
  echo "==> Updating desktop database"
  update-desktop-database "$APP_DIR" 2>/dev/null || true
fi

echo "==> Verify"
command -v ytsdownloader || true
which -a ytsdownloader 2>/dev/null || true
ls -la "$WRAPPER" "$DESKTOP"
echo "OK: launch with: ytsdownloader"
echo "Note: dist/ freeze (if present) is build output only — not registered on PATH."
