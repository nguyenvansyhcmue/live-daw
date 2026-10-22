#!/bin/zsh
# Candidate only: expands the direct hard-tune A->B->A chatter guard.
set -euo pipefail
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
RUNNER="$DAW_ROOT/build-calibration-arm64/StudioForgeCalibrationRunner"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST="/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
PATCH="/Users/hiimdrdey/autotune/vibe-hard-tune-reversal-guard-config.patch"
GUARD_MS="${VIBE_HARD_TUNE_RAPID_REVERSAL_GUARD_MS:-64}"
[[ "$GUARD_MS" == <-> ]] || { print -u2 "Guard must be an integer millisecond value."; exit 64; }
BUILD="${VIBE_REVERSAL_GUARD_BUILD:-$VIBE_ROOT/build-reversal-guard-$GUARD_MS}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-reversal-guard$GUARD_MS-$STAMP"
[[ -f "$RAW" && -x "$RUNNER" && -f "$ARTIST" ]] || { print -u2 "Missing fixture, runner, or Artist reference."; exit 66; }
cd "$VIBE_ROOT"
if ! rg -q 'VIBE_HARD_TUNE_RAPID_REVERSAL_GUARD_SECONDS' VibeAutotune/CorrectionTrajectory.h; then git apply "$PATCH"; fi
cmake -S "$VIBE_ROOT" -B "$BUILD" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="-DVIBE_HARD_TUNE_RAPID_REVERSAL_GUARD_SECONDS=$(awk "BEGIN { print $GUARD_MS / 1000.0 }")" \
  -DVIBE_JUCE_SOURCE_DIR="$DAW_ROOT/build-macos-arm64/_deps/juce-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR="$VIBE_ROOT/.third_party/signalsmith_linear-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH="$VIBE_ROOT/.third_party/signalsmith_stretch-src"
cmake --build "$BUILD" --target VibeAutotune_VST3 --parallel 8
CANDIDATE="$BUILD/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
mkdir -p "$OUT/vibe"
"$RUNNER" "$RAW" "$OUT/vibe" VibeAutotune "$CANDIDATE" | tee "$OUT/vibe-runner.log"
cp "$ARTIST" "$OUT/artist-reference-calibration-report.csv"
python3 "$ANALYSER" "$RAW" "$OUT/vibe/calibration-report.csv" "$OUT/artist-reference-calibration-report.csv" "$OUT/comparison"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 /Users/hiimdrdey/autotune/fit_studioforge_transitions.py "$RAW" "$OUT/vibe/calibration-report.csv" "$OUT/artist-reference-calibration-report.csv" "$OUT/transitions" --pitch-tools "$VIBE_ROOT/tools"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 /Users/hiimdrdey/autotune/analyze_hook2_correction_transfer.py "$RAW" "$OUT/artist-reference-calibration-report.csv" "$OUT/vibe/calibration-report.csv" "$OUT/transfer" --pitch-tools "$VIBE_ROOT/tools"
print "CANDIDATE COMPLETE (not installed; hard-tune reversal guard $GUARD_MS ms): $OUT"
print "Read: $OUT/comparison/calibration-report.md"
print "Transitions: $OUT/transitions/transition-summary.csv"
print "Transfer: $OUT/transfer/transfer-report.md"
