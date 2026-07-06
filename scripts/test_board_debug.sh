#!/bin/sh
set -eu

APP_DIR="${APP_DIR:-/home/aicps/Voice-Interface-V2}"
TEXT="${1:-dog sit then walk forward}"

cd "$APP_DIR"

if [ -x "$APP_DIR/.venv/bin/python" ]; then
  PYTHON="$APP_DIR/.venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi

exec "$PYTHON" -u "$APP_DIR/main.py" --debug "$TEXT" --dry-run
