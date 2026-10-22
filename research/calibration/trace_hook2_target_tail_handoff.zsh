#!/bin/zsh
# Renderer-only A/B for rapid target handoff. No plug-in is installed.
# The candidate rewrites only still-future OLA tail weights after a committed
# target change; selection, timing, latency and user parameters stay fixed.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
BUILD="${VIBE_BUILD:-$VIBE_ROOT/build-studioforge-juce8-stable}"
DIAGNOSTIC="$BUILD/VibeAutotuneSignalChainDiagnostic"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST_REPORT="/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
OLD_TAIL_GAIN="${VIBE_TARGET_TAIL_OLD_GAIN:-0.65}"
FADE_HALF_WINDOWS="${VIBE_TARGET_TAIL_FADE_HALF_WINDOWS:-0.25}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-target-tail-handoff-$STAMP"

[[ -f "$RAW" && -f "$ANALYSER" && -f "$ARTIST_REPORT" ]] || {
  print -u2 "Missing Hook-2 WAV, Artist reference, or calibration analyser."
  exit 66
}

cmake --build "$BUILD" --target VibeAutotuneSignalChainDiagnostic --parallel 1
[[ -x "$DIAGNOSTIC" ]] || { print -u2 "Diagnostic executable not built: $DIAGNOSTIC"; exit 67; }
mkdir -p "$OUT/baseline" "$OUT/target_tail"

run_case() {
  local destination="$1"
  local enable_tail="$2"
  # 0/0/0/0 is the exact hard-tune Artist-comparison surface. The final six
  # fields select target-tail replacement and its renderer-only shape.
  "$DIAGNOSTIC" "$RAW" "$destination" \
    0 1 0 0 0 0 1 0 0 0 0 - 1 \
    0.250 -0.150 0.666 0 0 0 4 11 50 -1 \
    "$enable_tail" 0 "$FADE_HALF_WINDOWS" "$OLD_TAIL_GAIN" 50 \
    > "$destination/runner.log"
}

run_case "$OUT/baseline" 0
run_case "$OUT/target_tail" 1

for name in baseline target_tail; do
  printf 'case,retune_ms,flex_tune,humanize,natural_vibrato,output\n0,0,0,0,0,"%s"\n' \
    "$OUT/$name/full_default_render.wav" > "$OUT/$name/calibration-report.csv"
  python3 "$ANALYSER" "$RAW" "$OUT/$name/calibration-report.csv" \
    "$ARTIST_REPORT" "$OUT/$name/comparison"
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
    python3 /Users/hiimdrdey/autotune/fit_studioforge_transitions.py "$RAW" \
      "$OUT/$name/calibration-report.csv" "$ARTIST_REPORT" "$OUT/$name/transitions" \
      --pitch-tools "$VIBE_ROOT/tools"
done

for name in baseline target_tail; do
  awk -F, '
    NR == 1 || ($1 == 0 && $2 == 0 && $3 == 0 && $4 == 0 && $5 >= 3.50 && $5 <= 3.90)
  ' "$OUT/$name/transitions/transition-events.csv" > "$OUT/$name-reversal-events.csv"
done

print ""
print "TRACE COMPLETE (renderer diagnostic only; not installed): $OUT"
print "Baseline:  $OUT/baseline/comparison/calibration-report.md"
print "Candidate: $OUT/target_tail/comparison/calibration-report.md"
print "Window A/B: $OUT/baseline-reversal-events.csv"
print "             $OUT/target_tail-reversal-events.csv"
