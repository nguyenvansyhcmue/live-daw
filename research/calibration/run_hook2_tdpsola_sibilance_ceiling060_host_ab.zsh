#!/bin/zsh
# One-variable host A/B: causal detector plus a 0.60 residual ceiling.
# Diagnostic only: no install, signing, or replacement of plug-in bundles.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
RUNNER="${STUDIOFORGE_CALIBRATION_RUNNER:-$DAW_ROOT/build-calibration-arm64/StudioForgeCalibrationRunner}"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST="$ROOT/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
JUCE="$DAW_ROOT/build-macos-arm64/_deps/juce-src"
LINEAR="$VIBE_ROOT/.third_party/signalsmith_linear-src"
STRETCH="$VIBE_ROOT/.third_party/signalsmith_stretch-src"
BUILD="$VIBE_ROOT/build-hook2-tdpsola-sibilance-ceiling060"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$ROOT/artifacts/hook2-tdpsola-sibilance-ceiling060-$STAMP"

zsh "$ROOT/apply_tdpsola_causal_sibilance_probe.zsh"
zsh "$ROOT/apply_tdpsola_sibilance_residual_ceiling.zsh"
for item in "$RAW" "$RUNNER" "$ANALYSER" "$ARTIST" "$JUCE/CMakeLists.txt" "$LINEAR/CMakeLists.txt" "$STRETCH/CMakeLists.txt"; do
  [[ -e "$item" ]] || { print -u2 "Missing required input: $item"; exit 66; }
done

flags='-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_TDPSOLA_CAUSAL_SIBILANCE_ENVELOPE=1 -DVIBE_TDPSOLA_SIBILANCE_MAX_RESIDUAL_MIX=0.60 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_RAPID_ADJACENT_EVIDENCE_WINDOW_FRAMES=8 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=1024 -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=128'
cmake -S "$VIBE_ROOT" -B "$BUILD" -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release \
  -DVIBE_JUCE_SOURCE_DIR:PATH="$JUCE" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$LINEAR" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$STRETCH" \
  -DCMAKE_CXX_FLAGS:STRING="$flags"
cmake --build "$BUILD" --target VibeAutotune_VST3 --parallel 4
CANDIDATE="$BUILD/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
[[ -d "$CANDIDATE" ]] || { print -u2 'Candidate VST3 missing'; exit 67; }
mkdir -p "$OUT/vibe"
"$RUNNER" "$RAW" "$OUT/vibe" VibeAutotune "$CANDIDATE" | tee "$OUT/host-runner.log"
awk -F, 'NR == 1 || $1 == 0' "$OUT/vibe/calibration-report.csv" > "$OUT/vibe-hardtune-report.csv"
awk -F, 'NR == 1 || $1 == 0' "$ARTIST" > "$OUT/artist-hardtune-report.csv"
python3 "$ANALYSER" "$RAW" "$OUT/vibe-hardtune-report.csv" "$OUT/artist-hardtune-report.csv" "$OUT/comparison"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ROOT/fit_studioforge_transitions.py" "$RAW" "$OUT/vibe-hardtune-report.csv" "$OUT/artist-hardtune-report.csv" "$OUT/transitions" --pitch-tools "$VIBE_ROOT/tools"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ROOT/analyze_hook2_correction_transfer.py" "$RAW" "$OUT/artist-hardtune-report.csv" "$OUT/vibe-hardtune-report.csv" "$OUT/transfer" --pitch-tools "$VIBE_ROOT/tools"
python3 "$ROOT/analyze_hook2_transition_outliers.py" "$OUT/transitions/transition-events.csv"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ROOT/analyze_sibilance_ab.py" "$RAW" \
  "$ROOT/artifacts/hook2-artist-vibe-20261014-041857/artist/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav" \
  "$OUT/vibe/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav" "$OUT/sibilance-regions.csv" \
  --pitch-tools "$VIBE_ROOT/tools" --top 30
print ''
print "HOST A/B COMPLETE (not installed; causal sibilance ceiling 0.60): $OUT"
print "Pitch:     $OUT/comparison/calibration-report.md"
print "Transfer:  $OUT/transfer/transfer-report.md"
print "Sibilance: $OUT/sibilance-regions.csv"
