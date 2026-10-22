#!/bin/zsh
# Re-render the currently installed Vibe VST3 and compare it with the frozen,
# previously verified Artist reference. Artist is not instantiated here, so a
# transient Audio Unit registry failure cannot turn an A/B DSP run into a
# misleading Vibe result.
set -euo pipefail

ROOT=/Users/hiimdrdey/code/daw
RAW="${VIBE_RAW_WAV:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
VIBE='/Users/hiimdrdey/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3'
RUNNER="$ROOT/build-calibration-arm64/StudioForgeCalibrationRunner"
ANALYSER="$ROOT/Tools/analyze_studioforge_calibration.py"
FIT=/Users/hiimdrdey/autotune/fit_studioforge_transitions.py
ARTIST=/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv
STAMP=$(date +%Y%m%d-%H%M%S)
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-installed-vibe-ab-$STAMP"

[[ -x "$RUNNER" && -f "$RAW" && -d "$VIBE" && -f "$ARTIST" ]] || {
  print -u2 'Missing runner, raw WAV, installed Vibe, or verified Artist reference.'
  exit 1
}
mkdir -p "$OUT/vibe"
"$RUNNER" "$RAW" "$OUT/vibe" VibeAutotune "$VIBE" | tee "$OUT/vibe-runner.log"
cp "$ARTIST" "$OUT/artist-reference-calibration-report.csv"
python3 "$ANALYSER" "$RAW" "$OUT/vibe/calibration-report.csv" \
  "$OUT/artist-reference-calibration-report.csv" "$OUT/comparison"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
python3 "$FIT" "$RAW" "$OUT/vibe/calibration-report.csv" \
  "$OUT/artist-reference-calibration-report.csv" "$OUT/transitions" \
  --pitch-tools "$ROOT/autotune/tools"
print "COMPLETE: $OUT"
print "Read: $OUT/comparison/calibration-report.md"
print "Transitions: $OUT/transitions/transition-summary.csv"
