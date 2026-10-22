#!/bin/zsh
set -euo pipefail

CONTENTS_DIR="${0:A:h:h}"
RUNTIME_DIR="$CONTENTS_DIR/Resources/tune-AI"
PYTHON="$RUNTIME_DIR/.venv/bin/python3"

if [[ ! -x "$PYTHON" ]]; then
  osascript -e 'display alert "Tune-AI runtime is missing" message "Re-run the Live DAW packaging script to restore the Python runtime." as critical'
  exit 1
fi

cd "$RUNTIME_DIR"
export PYTHONDONTWRITEBYTECODE=1
LOG_DIR="$HOME/Library/Logs/Tune-AI"
mkdir -p "$LOG_DIR"
exec "$PYTHON" "$RUNTIME_DIR/main.py" >>"$LOG_DIR/app.log" 2>&1
