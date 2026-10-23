#!/usr/bin/env bash
# Build optional native sidecars into native/bin/ (fail soft per toolchain).
# Fish-safe: ./scripts/build_natives.sh
# Optional: YTS_NATIVE_DIR=/path  (install prefix; default: <repo>/native/bin)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${YTS_NATIVE_DIR:-$ROOT/native/bin}"
mkdir -p "$OUT"

export PATH="${HOME}/.local/go-sdk/go/bin:${HOME}/.cargo/bin:${PATH:-}"

built=0
skipped=0

echo "Native install dir: $OUT"

# --- Rust: yts-normalize ---
if command -v cargo >/dev/null 2>&1; then
  echo "[rust] building yts-normalize…"
  (
    cd "$ROOT/native/rust/yts-normalize"
    cargo build --release
  )
  install -m 755 "$ROOT/native/rust/yts-normalize/target/release/yts-normalize" "$OUT/yts-normalize"
  built=$((built + 1))
  echo "[rust] ok → $OUT/yts-normalize"
else
  echo "[rust] skip (cargo not found)"
  skipped=$((skipped + 1))
fi

# --- C (preferred) or Zig: yts-prio ---
prio_done=0
if command -v cc >/dev/null 2>&1 || command -v gcc >/dev/null 2>&1; then
  CC_BIN="$(command -v cc || command -v gcc)"
  echo "[c] building yts-prio…"
  "$CC_BIN" -O2 -Wall -Wextra -o "$OUT/yts-prio" "$ROOT/native/c/yts-prio.c"
  chmod 755 "$OUT/yts-prio"
  built=$((built + 1))
  prio_done=1
  echo "[c] ok → $OUT/yts-prio"
fi
if [[ "$prio_done" -eq 0 ]] && command -v zig >/dev/null 2>&1; then
  # Zig 0.17 freestanding build-exe no longer offers @cImport; use zig cc on the C sources.
  echo "[zig cc] building yts-prio from native/c/yts-prio.c…"
  if zig cc -O2 -Wall -Wextra -o "$OUT/yts-prio" "$ROOT/native/c/yts-prio.c"
  then
    chmod 755 "$OUT/yts-prio"
    built=$((built + 1))
    prio_done=1
    echo "[zig cc] ok → $OUT/yts-prio"
  else
    echo "[zig cc] build failed"
    skipped=$((skipped + 1))
  fi
fi
if [[ "$prio_done" -eq 0 ]]; then
  echo "[c/zig] skip yts-prio (no cc/gcc/zig)"
  skipped=$((skipped + 1))
fi

# --- Go: yts-inbox ---
if command -v go >/dev/null 2>&1; then
  echo "[go] building yts-inbox…"
  (
    cd "$ROOT/native/go/yts-inbox"
    CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o "$OUT/yts-inbox" .
  )
  chmod 755 "$OUT/yts-inbox"
  built=$((built + 1))
  echo "[go] ok → $OUT/yts-inbox"
else
  echo "[go] skip (go not found)"
  skipped=$((skipped + 1))
fi

# --- Ruby filter (script copy; needs ruby at runtime) ---
if [[ -f "$ROOT/native/ruby/yts_json_filter.rb" ]]; then
  install -m 755 "$ROOT/native/ruby/yts_json_filter.rb" "$OUT/yts_json_filter.rb"
  echo "[ruby] installed script → $OUT/yts_json_filter.rb"
  if command -v ruby >/dev/null 2>&1; then
    built=$((built + 1))
  else
    echo "[ruby] note: ruby not on PATH — script installed but unused until ruby is available"
    skipped=$((skipped + 1))
  fi
fi

echo
echo "Done: built/installed=$built  skipped=$skipped"
echo "Suite uses these automatically when present; Python fallbacks apply otherwise."
echo "Disable: YTS_USE_NATIVE=0"
