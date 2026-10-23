#!/usr/bin/env bash
# Install a single user-local launcher for this repo (dev install).
# Fish-safe: never sources activate scripts; uses .venv/bin/python only.
# Does not register dist/ freeze binaries — keep one source of truth.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_HOME/applications"
ICON_NAME="ytsdownloader"
ICON_SRC_DIR="$ROOT/assets/icons"
HICOLOR="$DATA_HOME/icons/hicolor"
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

echo "==> Installing icons under $HICOLOR"
if [[ -f "$ICON_SRC_DIR/scalable/ytsdownloader.svg" ]]; then
  mkdir -p "$HICOLOR/scalable/apps"
  install -m 644 "$ICON_SRC_DIR/scalable/ytsdownloader.svg" \
    "$HICOLOR/scalable/apps/${ICON_NAME}.svg"
fi
for size in 256 128 64 48 32; do
  src="$ICON_SRC_DIR/${size}x${size}/ytsdownloader.png"
  if [[ -f "$src" ]]; then
    mkdir -p "$HICOLOR/${size}x${size}/apps"
    install -m 644 "$src" "$HICOLOR/${size}x${size}/apps/${ICON_NAME}.png"
  fi
done
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$HICOLOR" 2>/dev/null || true
elif command -v update-icon-caches >/dev/null 2>&1; then
  update-icon-caches "$HICOLOR" 2>/dev/null || true
fi

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
Icon=$ICON_NAME
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
