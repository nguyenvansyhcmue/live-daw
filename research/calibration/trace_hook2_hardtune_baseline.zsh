#!/bin/zsh
# Production-host evidence for the one preset that must be solved first:
# Alto, F# Natural Minor, Retune/Flex/Humanize/Natural Vibrato all at zero.
# It reads the selected VST3 only; it does not install, sign, or edit it.
set -euo pipefail

DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
VIBE_ROOT="${VIBE_ROOT:-$DAW_ROOT/autotune}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
RUNNER="${STUDIOFORGE_CALIBRATION_RUNNER:-$DAW_ROOT/build-calibration-arm64/StudioForgeCalibrationRunner}"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST="/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
VST3="${VIBE_HARDTUNE_VST3:-/Users/hiimdrdey/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-hardtune-baseline-$STAMP"

[[ -f "$RAW" && -x "$RUNNER" && -f "$ANALYSER" && -f "$ARTIST" && -d "$VST3" ]] || {
  print -u2 "Missing raw WAV, host runner, analyser, Artist reference, or Vibe VST3."
  exit 66
}
mkdir -p "$OUT/vibe"

# The runner renders its fixed matrix, but all downstream analysis below reads
# only case 0 (0/0/0/0). Its host configuration locks Alto/F#/Natural Minor.
"$RUNNER" "$RAW" "$OUT/vibe" VibeAutotune "$VST3" | tee "$OUT/host-runner.log"

awk -F, 'NR == 1 || $1 == 0' "$OUT/vibe/calibration-report.csv" > "$OUT/vibe-hardtune-report.csv"
awk -F, 'NR == 1 || $1 == 0' "$ARTIST" > "$OUT/artist-hardtune-report.csv"

python3 "$ANALYSER" "$RAW" "$OUT/vibe-hardtune-report.csv" \
  "$OUT/artist-hardtune-report.csv" "$OUT/comparison"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
  python3 /Users/hiimdrdey/autotune/fit_studioforge_transitions.py "$RAW" \
    "$OUT/vibe-hardtune-report.csv" "$OUT/artist-hardtune-report.csv" "$OUT/transitions" \
    --pitch-tools "$VIBE_ROOT/tools"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
  python3 /Users/hiimdrdey/autotune/analyze_hook2_correction_transfer.py "$RAW" \
    "$OUT/artist-hardtune-report.csv" "$OUT/vibe-hardtune-report.csv" "$OUT/transfer" \
    --pitch-tools "$VIBE_ROOT/tools"
python3 /Users/hiimdrdey/autotune/analyze_hook2_transition_outliers.py \
  "$OUT/transitions/transition-events.csv"

print ""
print "HARD-TUNE BASELINE COMPLETE (selected VST3 not modified): $OUT"
print "Read first: $OUT/comparison/calibration-report.md"
print "Outliers:   $OUT/transitions/transition-outlier-report.md"
print "Transfer:   $OUT/transfer/transfer-report.md"
