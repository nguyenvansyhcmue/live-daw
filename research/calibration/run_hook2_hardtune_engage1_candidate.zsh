#!/bin/zsh
# Offline A/B only. This candidate changes just the hard-tune renderer
# lifecycle entry from two certified 128-sample control ticks to one.  It is
# never installed, signed, or used by StudioForge's production plug-in path.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
BUILD="${VIBE_HARDTUNE_ENGAGE1_BUILD:-$VIBE_ROOT/build-hardtune-engage1}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
RUNNER="$DAW_ROOT/build-calibration-arm64/StudioForgeCalibrationRunner"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST="/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
PATCH="/Users/hiimdrdey/autotune/vibe-hard-tune-engage-gate-config.patch"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-hardtune-engage1-$STAMP"

[[ -f "$RAW" && -x "$RUNNER" && -f "$ARTIST" ]] || {
  print -u2 "Missing Hook-2 fixture, calibration runner, or frozen Artist reference."
  exit 66
}

cd "$VIBE_ROOT"
if git apply --reverse --check "$PATCH" >/dev/null 2>&1; then
  print "Hard-tune engage-gate configuration hook already present."
else
  git apply "$PATCH"
  print "Applied hard-tune engage-gate configuration hook."
fi

cmake -S "$VIBE_ROOT" -B "$BUILD" -G "Unix Makefiles" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="-DVIBE_HARD_TUNE_ENGAGE_CONTROL_FRAMES=1" \
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
print "CANDIDATE COMPLETE (not installed): $OUT"
print "Read: $OUT/comparison/calibration-report.md"
print "Transitions: $OUT/transitions/transition-summary.csv"
print "Transfer: $OUT/transfer/transfer-report.md"
