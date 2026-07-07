#!/bin/sh
set -eu

APP_DIR="${APP_DIR:-/home/unitree/Voice-Interface-V2/Voice-Interface-V2}"
cd "$APP_DIR"

echo "Starting dog command receiver from $APP_DIR"
exec python3 -u "$APP_DIR/dog/receiver.py"
