#!/bin/zsh
# A/B only: increase spectral control cadence for the exact hard-tune test.
# This never installs, signs, or replaces the user's VST3.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
RUNNER="${STUDIOFORGE_CALIBRATION_RUNNER:-$DAW_ROOT/build-calibration-arm64/StudioForgeCalibrationRunner}"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST="/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
PATCH="/Users/hiimdrdey/autotune/vibe-spectral-hop-config.patch"
HOP="${VIBE_SPECTRAL_HOP:-64}"
BUILD="${VIBE_SPECTRAL_HOP_BUILD:-$VIBE_ROOT/build-hardtune-spectral-hop-$HOP}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-hardtune-spectral-hop$HOP-$STAMP"

[[ "$HOP" == <-> && "$HOP" -ge 32 && "$HOP" -le 128 ]] || {
  print -u2 "VIBE_SPECTRAL_HOP must be an integer from 32 to 128."
  exit 64
}
[[ -f "$RAW" && -x "$RUNNER" && -f "$ANALYSER" && -f "$ARTIST" ]] || {
  print -u2 "Missing Hook-2 WAV, host runner, analyser, or Artist reference."
  exit 66
}

cd "$VIBE_ROOT"
if ! rg -q 'VIBE_SPECTRAL_HOP_SAMPLES' VibeAutotune/SignalsmithPitchRenderer.h; then
  git apply "$PATCH"
fi
cmake -S "$VIBE_ROOT" -B "$BUILD" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="-DVIBE_SPECTRAL_HOP_SAMPLES=$HOP" \
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
print "CANDIDATE COMPLETE (not installed; spectral 1024/$HOP): $OUT"
print "Read first: $OUT/comparison/calibration-report.md"
print "Outliers:   $OUT/transitions/transition-outlier-report.md"
print "Transfer:   $OUT/transfer/transfer-report.md"
