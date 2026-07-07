#!/bin/sh
set -eu

APP_DIR="${APP_DIR:-/home/unitree/Voice-Interface-V2/Voice-Interface-V2}"
cd "$APP_DIR"

export PYTHONPATH="/home/unitree/unitree_sdk2_python:${PYTHONPATH:-}"
export PYTHONPATH="/home/unitree/.local/lib/python3.8/site-packages:${PYTHONPATH:-}"
export LD_LIBRARY_PATH="/home/unitree/unitree_ros2/cyclonedds_ws/install/cyclonedds/lib:${LD_LIBRARY_PATH:-}"

echo "Starting dog command receiver from $APP_DIR"
exec python3 -u "$APP_DIR/dog/receiver.py" --host "${DOG_WIRED_IP:-10.42.0.1}" --port "${DOG_COMMAND_PORT:-5005}"
