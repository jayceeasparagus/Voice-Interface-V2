#!/bin/sh
set -eu

APP_DIR="${APP_DIR:-/home/aicps/Voice-Interface-V2}"
cd "$APP_DIR"

if [ -x "$APP_DIR/.venv/bin/python" ]; then
  PYTHON="$APP_DIR/.venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi

echo "Starting board voice pipeline from $APP_DIR"
echo "Python: $PYTHON"
exec "$PYTHON" -u "$APP_DIR/main.py"
