#!/bin/zsh
# Read-only forensic comparison of the remaining 4.4–4.8 s hard-tune mismatch.
# It does not build, patch, install, or sign any plug-in.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
TOOLS="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}/tools"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
ARTIST="${HOOK2_ARTIST:-$ROOT/artifacts/hook2-artist-vibe-20261014-041857/artist/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav}"
# Default to the currently promoted diagnostic baseline.  A caller can always
# pass HOOK2_VIBE to inspect an uninstalled sweep arm instead.
VIBE="${HOOK2_VIBE:-$ROOT/artifacts/hook2-adjacent-dwell-sweep-20261016-034136/dwell_80ms/full_default_render.wav}"
OUT="$ROOT/artifacts/hook2-hardtune-4631-window-$(date +%Y%m%d-%H%M%S)"

for required_file in "$RAW" "$ARTIST" "$VIBE" "$TOOLS/compare_pitch_correction_bounces.py"; do
  [[ -f "$required_file" ]] || { print -u2 "Missing required file: $required_file"; exit 2; }
done

mkdir -p "$OUT"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ROOT/analyze_hook2_pitch_window.py" \
  "$RAW" "$ARTIST" "$VIBE" "$OUT" --pitch-tools "$TOOLS" --start 4.20 --end 4.85

print ""
print "FORENSIC WINDOW COMPLETE (read-only; not installed): $OUT"
print "Read: $OUT/pitch-window-report.md"
print "Frames: $OUT/pitch-window.csv"
