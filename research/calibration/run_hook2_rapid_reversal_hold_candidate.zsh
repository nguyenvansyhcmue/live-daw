#!/bin/zsh
# Offline A/B for the hard-tune A -> B -> A plateau only. It never installs
# or signs a plug-in. The production defaults remain unchanged.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
RUNNER="$DAW_ROOT/build-calibration-arm64/StudioForgeCalibrationRunner"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST="/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"

# Keep the measured 16-ms adjacent admission candidate fixed. This trial
# isolates only the audible B plateau during a confirmed rapid reversal.
DWELL_SAMPLES="${VIBE_RAPID_ADJACENT_DWELL_SAMPLES:-768}"
HOLD_SAMPLES="${VIBE_HARD_LOCK_RAPID_REVERSAL_HOLD_SAMPLES:-512}"
[[ "$DWELL_SAMPLES" == <-> && "$DWELL_SAMPLES" -ge 256 && "$DWELL_SAMPLES" -le 3840 ]] || {
  print -u2 "VIBE_RAPID_ADJACENT_DWELL_SAMPLES must be an integer from 256 to 3840."
  exit 64
}
[[ "$HOLD_SAMPLES" == <-> && "$HOLD_SAMPLES" -ge 128 && "$HOLD_SAMPLES" -le 1024 ]] || {
  print -u2 "VIBE_HARD_LOCK_RAPID_REVERSAL_HOLD_SAMPLES must be an integer from 128 to 1024."
  exit 64
}

BUILD="${VIBE_RAPID_REVERSAL_HOLD_BUILD:-$VIBE_ROOT/build-rapid-reversal-hold-$HOLD_SAMPLES}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-rapid-reversal-hold${HOLD_SAMPLES}-$STAMP"

[[ -f "$RAW" && -x "$RUNNER" && -f "$ARTIST" ]] || {
  print -u2 "Missing Hook-2 fixture, calibration runner, or frozen Artist reference."
  exit 66
}

cd "$VIBE_ROOT"
cmake -S "$VIBE_ROOT" -B "$BUILD" -G "Unix Makefiles" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="-DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=$DWELL_SAMPLES -DVIBE_HARD_LOCK_RAPID_REVERSAL_HOLD_SAMPLES=$HOLD_SAMPLES" \
  -DVIBE_JUCE_SOURCE_DIR="$DAW_ROOT/build-macos-arm64/_deps/juce-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR="$VIBE_ROOT/.third_party/signalsmith_linear-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH="$VIBE_ROOT/.third_party/signalsmith_stretch-src"
cmake --build "$BUILD" --target VibeAutotune_VST3 --parallel 8

CANDIDATE="$BUILD/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
[[ -d "$CANDIDATE" ]] || { print -u2 "Candidate VST3 was not built: $CANDIDATE"; exit 1; }
mkdir -p "$OUT/vibe"
"$RUNNER" "$RAW" "$OUT/vibe" VibeAutotune "$CANDIDATE" | tee "$OUT/vibe-runner.log"
cp "$ARTIST" "$OUT/artist-reference-calibration-report.csv"
python3 "$ANALYSER" "$RAW" "$OUT/vibe/calibration-report.csv" \
  "$OUT/artist-reference-calibration-report.csv" "$OUT/comparison"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
python3 /Users/hiimdrdey/autotune/fit_studioforge_transitions.py "$RAW" \
  "$OUT/vibe/calibration-report.csv" "$OUT/artist-reference-calibration-report.csv" \
  "$OUT/transitions" --pitch-tools "$VIBE_ROOT/tools"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
python3 /Users/hiimdrdey/autotune/analyze_hook2_correction_transfer.py "$RAW" \
  "$OUT/artist-reference-calibration-report.csv" "$OUT/vibe/calibration-report.csv" \
  "$OUT/transfer" --pitch-tools "$VIBE_ROOT/tools"

print ""
print "CANDIDATE COMPLETE (not installed; reversal hold ${HOLD_SAMPLES} samples): $OUT"
print "Read: $OUT/comparison/calibration-report.md"
print "Transitions: $OUT/transitions/transition-summary.csv"
print "Transfer: $OUT/transfer/transfer-report.md"
