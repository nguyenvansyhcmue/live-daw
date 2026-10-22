#!/bin/bash
set -euo pipefail

workspace_root="$(cd "$(dirname "$0")/.." && pwd)"
tune_ai_root="$workspace_root/tune-AI"
pyinstaller="$tune_ai_root/.venv/bin/pyinstaller"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Tune-AI macOS packaging must run on macOS" >&2
    exit 2
fi
if [[ ! -x "$pyinstaller" ]]; then
    echo "Missing PyInstaller environment: $pyinstaller" >&2
    echo "Create tune-AI/.venv and install the locked macOS dependencies first." >&2
    exit 3
fi

# Keep PyInstaller's binary-rewrite cache inside the repository workspace.
# This works on locked-down CI runners and prevents a developer's global cache
# from silently influencing the release.
export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$tune_ai_root/.pyinstaller-cache}"
cd "$tune_ai_root"
"$pyinstaller" --noconfirm "THM Vocal Panel.spec"

app="$tune_ai_root/dist/THM Vocal Panel.app"
[[ -d "$app" ]] || { echo "PyInstaller did not produce $app" >&2; exit 4; }
echo "Built: $app"
