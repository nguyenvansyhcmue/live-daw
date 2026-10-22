#!/bin/zsh
# Candidate only: +/-240 cents only for non-vibrato musical presets through
# Retune 50 ms. Hard Tune, Natural Vibrato and Retune 100 ms remain +/-120.
set -euo pipefail
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
RUNNER="$DAW_ROOT/build-calibration-arm64/StudioForgeCalibrationRunner"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST="/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
BASE_PATCH="/Users/hiimdrdey/autotune/vibe-correction-rail-config.patch"
MUSICAL_PATCH="/Users/hiimdrdey/autotune/vibe-musical-correction-rail-config.patch"
PATCH="/Users/hiimdrdey/autotune/vibe-fast-musical-correction-rail-config.patch"
DELIVERY_PATCH="/Users/hiimdrdey/autotune/vibe-fast-musical-delivery-rail.patch"
RAIL="${VIBE_MUSICAL_MAXIMUM_LIVE_CORRECTION_CENTS:-240}"
MAX_RETUNE="${VIBE_MUSICAL_RAIL_MAX_RETUNE_MS:-50}"
[[ "$RAIL" == <-> && "$MAX_RETUNE" == <-> ]] || { print -u2 "Rail and maximum retune must be integer values."; exit 64; }
BUILD="${VIBE_FAST_MUSICAL_RAIL_BUILD:-$VIBE_ROOT/build-fast-musical-rail-$RAIL}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-fast-musical-rail${RAIL}-r${MAX_RETUNE}-$STAMP"
[[ -f "$RAW" && -x "$RUNNER" && -f "$ARTIST" ]] || { print -u2 "Missing fixture, runner, or Artist reference."; exit 66; }
cd "$VIBE_ROOT"
SOURCE="$VIBE_ROOT/VibeAutotune/CorrectionTrajectory.h"
# Later candidate patches intentionally edit the same source lines. Detect
# durable source markers instead of reverse-applying an earlier diff, which
# would otherwise report a false conflict after a valid previous candidate.
if ! rg -q 'VIBE_MAXIMUM_LIVE_CORRECTION_CENTS' "$SOURCE"; then
  git apply "$BASE_PATCH"
fi
if ! rg -q 'VIBE_MUSICAL_MAXIMUM_LIVE_CORRECTION_CENTS' "$SOURCE"; then
  git apply "$MUSICAL_PATCH"
fi
if ! rg -q 'VIBE_MUSICAL_RAIL_MAX_RETUNE_MS' "$SOURCE"; then
  git apply "$PATCH"
fi
if ! rg -q 'rendererDeliveryRailCents' "$VIBE_ROOT/VibeAutotune/PluginProcessor.cpp"; then
  git apply "$DELIVERY_PATCH"
fi
cmake -S "$VIBE_ROOT" -B "$BUILD" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="-DVIBE_MUSICAL_MAXIMUM_LIVE_CORRECTION_CENTS=$RAIL -DVIBE_MUSICAL_RAIL_MAX_RETUNE_MS=$MAX_RETUNE" \
  -DVIBE_JUCE_SOURCE_DIR="$DAW_ROOT/build-macos-arm64/_deps/juce-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR="$VIBE_ROOT/.third_party/signalsmith_linear-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH="$VIBE_ROOT/.third_party/signalsmith_stretch-src"
cmake --build "$BUILD" --target VibeAutotune_VST3 --parallel 8
CANDIDATE="$BUILD/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
[[ -d "$CANDIDATE" ]] || { print -u2 "Candidate build missing."; exit 1; }
mkdir -p "$OUT/vibe"
"$RUNNER" "$RAW" "$OUT/vibe" VibeAutotune "$CANDIDATE" | tee "$OUT/vibe-runner.log"
cp "$ARTIST" "$OUT/artist-reference-calibration-report.csv"
python3 "$ANALYSER" "$RAW" "$OUT/vibe/calibration-report.csv" "$OUT/artist-reference-calibration-report.csv" "$OUT/comparison"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 /Users/hiimdrdey/autotune/fit_studioforge_transitions.py "$RAW" "$OUT/vibe/calibration-report.csv" "$OUT/artist-reference-calibration-report.csv" "$OUT/transitions" --pitch-tools "$VIBE_ROOT/tools"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 /Users/hiimdrdey/autotune/analyze_hook2_correction_transfer.py "$RAW" "$OUT/artist-reference-calibration-report.csv" "$OUT/vibe/calibration-report.csv" "$OUT/transfer" --pitch-tools "$VIBE_ROOT/tools"
print "CANDIDATE COMPLETE (not installed; +/-${RAIL} through Retune ${MAX_RETUNE} ms only): $OUT"
print "Read: $OUT/comparison/calibration-report.md"
print "Transitions: $OUT/transitions/transition-summary.csv"
print "Transfer: $OUT/transfer/transfer-report.md"
