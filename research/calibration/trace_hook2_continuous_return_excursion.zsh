#!/bin/zsh
# Isolated A/B of the existing continuous rapid-return trajectory candidate.
# It keeps the MIDI target selector unchanged and never installs a plug-in.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
BUILD="${VIBE_BUILD:-$VIBE_ROOT/build-studioforge-juce8-stable}"
DIAGNOSTIC="$BUILD/VibeAutotuneSignalChainDiagnostic"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST_REPORT="/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
FRAMES="${VIBE_CONTINUOUS_RETURN_FRAMES:-4}"
TRAVEL_CENTS="${VIBE_CONTINUOUS_RETURN_TRAVEL_CENTS:-11}"
HOLD_MS="${VIBE_CONTINUOUS_RETURN_HOLD_MS:-50}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-continuous-return-$STAMP"

[[ -f "$RAW" && -f "$ANALYSER" && -f "$ARTIST_REPORT" ]] || {
  print -u2 "Missing Hook-2 WAV, Artist reference, or calibration analyser."
  exit 66
}
[[ "$FRAMES" == <-> && "$FRAMES" -ge 2 && "$FRAMES" -le 12 ]] || {
  print -u2 "VIBE_CONTINUOUS_RETURN_FRAMES must be an integer from 2 to 12."
  exit 64
}

cmake --build "$BUILD" --target VibeAutotuneSignalChainDiagnostic --parallel 1
[[ -x "$DIAGNOSTIC" ]] || { print -u2 "Diagnostic executable not built: $DIAGNOSTIC"; exit 67; }
mkdir -p "$OUT/baseline" "$OUT/excursion"

# Args bind the Artist-comparison hard-tune F# Natural Minor preset.  The
# final six controls are diagnostic-only: rapid-return preview off, then the
# continuous excursion on, with its bounded evidence and hold tuning.
run_case() {
  local destination="$1"
  local continuous="$2"
  "$DIAGNOSTIC" "$RAW" "$destination" \
    0 1 0 0 0 0 1 0 0 0 0 - 1 \
    0.250 -0.150 0.666 0 "$continuous" 0 \
    "$FRAMES" "$TRAVEL_CENTS" "$HOLD_MS" > "$destination/runner.log"
}

run_case "$OUT/baseline" 0
run_case "$OUT/excursion" 1

for name in baseline excursion; do
  printf 'case,retune_ms,flex_tune,humanize,natural_vibrato,output\n0,0,0,0,0,"%s"\n' \
    "$OUT/$name/full_default_render.wav" > "$OUT/$name/calibration-report.csv"
  python3 "$ANALYSER" "$RAW" "$OUT/$name/calibration-report.csv" \
    "$ARTIST_REPORT" "$OUT/$name/comparison"
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
    python3 /Users/hiimdrdey/autotune/fit_studioforge_transitions.py "$RAW" \
      "$OUT/$name/calibration-report.csv" "$ARTIST_REPORT" "$OUT/$name/transitions" \
      --pitch-tools "$VIBE_ROOT/tools"
done

awk -F, '
  NR == 1 || ($1 == 0 && $2 == 0 && $3 == 0 && $4 == 0 && $5 >= 3.50 && $5 <= 3.90)
' "$OUT/baseline/transitions/transition-events.csv" > "$OUT/baseline-reversal-events.csv"
awk -F, '
  NR == 1 || ($1 == 0 && $2 == 0 && $3 == 0 && $4 == 0 && $5 >= 3.50 && $5 <= 3.90)
' "$OUT/excursion/transitions/transition-events.csv" > "$OUT/excursion-reversal-events.csv"

print ""
print "TRACE COMPLETE (diagnostic only; not installed): $OUT"
print "Baseline:  $OUT/baseline/comparison/calibration-report.md"
print "Excursion: $OUT/excursion/comparison/calibration-report.md"
print "Window A/B: $OUT/baseline-reversal-events.csv"
print "             $OUT/excursion-reversal-events.csv"
