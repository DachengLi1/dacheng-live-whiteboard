#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8788}"
cd "$DIR" || exit 1
nohup python3 serve_spa.py > /tmp/dacheng-live-whiteboard.log 2>&1 &
sleep 1
open "http://127.0.0.1:${PORT}/"
echo "Whiteboard is opening at http://127.0.0.1:${PORT}/"
