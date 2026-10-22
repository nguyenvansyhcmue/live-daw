#!/bin/zsh
# One forensic A/B: preview only the next legal scale target, never a skipped degree.
# It builds an uninstalled candidate; it never replaces the installed VST3.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
RUNNER="${STUDIOFORGE_CALIBRATION_RUNNER:-$DAW_ROOT/build-calibration-arm64/StudioForgeCalibrationRunner}"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST="/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
MODE_PATCH="/Users/hiimdrdey/autotune/vibe-tdpsola-host-ab-config.patch"
RAIL_PATCH="/Users/hiimdrdey/autotune/vibe-hardtune-correction-rail-config.patch"
PREVIEW_PATCH="/Users/hiimdrdey/autotune/vibe-hard-tune-preview-config.patch"
ADJACENT_PATCH="/Users/hiimdrdey/autotune/vibe-hard-tune-preview-adjacent-config.patch"
NEIGHBOUR_PATCH="/Users/hiimdrdey/autotune/vibe-hard-tune-preview-scale-neighbour-config.patch"
BUILD="${VIBE_TDPSOLA_PREVIEW_NEIGHBOUR_BUILD:-$VIBE_ROOT/build-hardtune-tdpsola-rail160-preview-neighbour}"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-tdpsola-rail160-preview-neighbour-$(date +%Y%m%d-%H%M%S)"

[[ -f "$RAW" && -x "$RUNNER" && -f "$ANALYSER" && -f "$ARTIST" ]] || {
  print -u2 "Missing Hook-2 WAV, host runner, analyser, or Artist reference."
  exit 66
}
cd "$VIBE_ROOT"
if ! rg -q 'VIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE' VibeAutotune/PluginProcessor.cpp; then git apply "$MODE_PATCH"; fi
if ! rg -q 'VIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS' VibeAutotune/CorrectionTrajectory.h; then git apply "$RAIL_PATCH"; fi
if ! rg -q 'VIBE_HARD_TUNE_TRAJECTORY_PREVIEW' VibeAutotune/CorrectionTrajectory.h; then git apply "$PREVIEW_PATCH"; fi
if ! rg -q 'previewIsAdjacent' VibeAutotune/CorrectionTrajectory.h; then git apply "$ADJACENT_PATCH"; fi
if ! rg -q 'previewIsNextLegalTarget' VibeAutotune/CorrectionTrajectory.h; then git apply "$NEIGHBOUR_PATCH"; fi

cmake -S "$VIBE_ROOT" -B "$BUILD" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1" \
  -DVIBE_JUCE_SOURCE_DIR="$DAW_ROOT/build-macos-arm64/_deps/juce-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR="$VIBE_ROOT/.third_party/signalsmith_linear-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH="$VIBE_ROOT/.third_party/signalsmith_stretch-src"
cmake --build "$BUILD" --target VibeAutotune_VST3 --parallel 8
CANDIDATE="$BUILD/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
[[ -d "$CANDIDATE" ]] || { print -u2 "Candidate VST3 missing: $CANDIDATE"; exit 67; }

mkdir -p "$OUT/vibe"
"$RUNNER" "$RAW" "$OUT/vibe" VibeAutotune "$CANDIDATE" | tee "$OUT/host-runner.log"
awk -F, 'NR == 1 || $1 == 0' "$OUT/vibe/calibration-report.csv" > "$OUT/vibe-hardtune-report.csv"
awk -F, 'NR == 1 || $1 == 0' "$ARTIST" > "$OUT/artist-hardtune-report.csv"
python3 "$ANALYSER" "$RAW" "$OUT/vibe-hardtune-report.csv" "$OUT/artist-hardtune-report.csv" "$OUT/comparison"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 /Users/hiimdrdey/autotune/fit_studioforge_transitions.py \
  "$RAW" "$OUT/vibe-hardtune-report.csv" "$OUT/artist-hardtune-report.csv" "$OUT/transitions" --pitch-tools "$VIBE_ROOT/tools"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 /Users/hiimdrdey/autotune/analyze_hook2_correction_transfer.py \
  "$RAW" "$OUT/artist-hardtune-report.csv" "$OUT/vibe-hardtune-report.csv" "$OUT/transfer" --pitch-tools "$VIBE_ROOT/tools"
python3 /Users/hiimdrdey/autotune/analyze_hook2_transition_outliers.py "$OUT/transitions/transition-events.csv"

print ""
print "HOST A/B COMPLETE (not installed; TD-PSOLA rail +/-160, next-legal-scale preview): $OUT"
print "Read first: $OUT/comparison/calibration-report.md"
print "Outliers:   $OUT/transitions/transition-outlier-report.md"
print "Transfer:   $OUT/transfer/transfer-report.md"
