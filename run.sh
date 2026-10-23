#!/usr/bin/env bash
# Shell-agnostic launcher (works from bash, fish, zsh without activating the venv).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec "$ROOT/.venv/bin/python" "$ROOT/main.py" "$@"
