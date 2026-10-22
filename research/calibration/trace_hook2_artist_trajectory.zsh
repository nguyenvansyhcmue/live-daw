#!/bin/zsh
# Read-only Artist curve inference against the TD-PSOLA 80-ms baseline.
set -euo pipefail
ROOT="/Users/hiimdrdey/autotune"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
ARTIST="${HOOK2_ARTIST:-$ROOT/artifacts/hook2-artist-vibe-20261014-041857/artist/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav}"
CASE="${HOOK2_CASE:-$ROOT/artifacts/hook2-adjacent-dwell-sweep-20261016-034136/dwell_80ms}"
TOOLS="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}/tools"
OUT="$ROOT/artifacts/hook2-artist-trajectory-$(date +%Y%m%d-%H%M%S)"
for required_file in "$RAW" "$ARTIST" "$CASE/full_default_intervals.csv" "$TOOLS/compare_pitch_correction_bounces.py"; do
  [[ -f "$required_file" ]] || { print -u2 "Missing required file: $required_file"; exit 2; }
done
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ROOT/analyze_artist_trajectory_delta.py" "$RAW" "$ARTIST" "$CASE/full_default_intervals.csv" "$OUT" --pitch-tools "$TOOLS"
printf '\nTRACE COMPLETE (read-only; not installed): %s\n' "$OUT"
printf 'Read: %s/artist-vibe-trajectory.md\n' "$OUT"
