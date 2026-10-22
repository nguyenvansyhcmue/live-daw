#!/bin/zsh
# A/B only: test whether the production spectral renderer's +/-165..182-cent
# ratio guard is suppressing the exact 0/0/0/0 hard-tune correction. No install.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
RUNNER="${STUDIOFORGE_CALIBRATION_RUNNER:-$DAW_ROOT/build-calibration-arm64/StudioForgeCalibrationRunner}"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST="/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
PATCH="/Users/hiimdrdey/autotune/vibe-hardtune-correction-rail-config.patch"
BUILD="${VIBE_HARDTUNE_SPECTRAL_RANGE_BUILD:-$VIBE_ROOT/build-hardtune-spectral-range}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-hardtune-spectral-range-$STAMP"

[[ -f "$RAW" && -x "$RUNNER" && -f "$ANALYSER" && -f "$ARTIST" ]] || {
  print -u2 "Missing Hook-2 WAV, host runner, analyser, or Artist reference."
  exit 66
}

cd "$VIBE_ROOT"
if ! rg -q 'VIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS' VibeAutotune/CorrectionTrajectory.h; then
  git apply "$PATCH"
fi

# +/-240 cents needs ratios 0.87055..1.14870. 0.87..1.15 adds only the
# missing headroom; it does not make a broad unbounded pitch-shifter.
cmake -S "$VIBE_ROOT" -B "$BUILD" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="-DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=240 -DVIBE_SPECTRAL_MIN_RATIO=0.87 -DVIBE_SPECTRAL_MAX_RATIO=1.15" \
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
print "CANDIDATE COMPLETE (not installed; spectral range 0.87..1.15): $OUT"
print "Read first: $OUT/comparison/calibration-report.md"
print "Outliers:   $OUT/transitions/transition-outlier-report.md"
print "Transfer:   $OUT/transfer/transfer-report.md"
