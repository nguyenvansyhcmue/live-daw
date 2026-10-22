#!/bin/zsh
set -euo pipefail
ROOT="/Users/hiimdrdey/autotune"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
CASE="${HOOK2_CASE:-$ROOT/artifacts/hook2-adjacent-dwell-sweep-20261016-034136/dwell_80ms}"
TOOLS="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}/tools"
OUT="$ROOT/artifacts/hook2-detector-midpoint-$(date +%Y%m%d-%H%M%S)"
[[ -f "$RAW" && -f "$CASE/full_default_intervals.csv" ]] || { print -u2 "Missing raw WAV or interval trace"; exit 2; }
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ROOT/audit_vibe_detector_midpoint.py" "$RAW" "$CASE/full_default_intervals.csv" "$OUT" --pitch-tools "$TOOLS"
printf '\nTRACE COMPLETE (read-only; not installed): %s\n' "$OUT"
printf 'Read: %s/detector-midpoint-report.md\n' "$OUT"
