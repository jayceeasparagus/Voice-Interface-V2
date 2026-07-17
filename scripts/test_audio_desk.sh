#!/bin/sh

cd "$(dirname "$0")/.."
python3 -m audio.listener --desk-test
