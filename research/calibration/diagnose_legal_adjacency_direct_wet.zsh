#!/bin/zsh
# Forensic renderer A/B only. Builds a disposable copy of the exact accepted
# candidate and never touches the installed VST3, package, or historical source.
set -euo pipefail

ROOT='/Users/hiimdrdey/autotune'
DAW='/Users/hiimdrdey/code/daw'
SOURCE="$ROOT/artifacts/crossing24-bounded-preview-20261017-113341/source"
RAW='/Users/hiimdrdey/Music/Music/Media.localized/Music/Unknown Artist/Unknown Album/hook2_raw_segment.wav'
RUNNER="$DAW/build-calibration-arm64/StudioForgeCalibrationRunner"
JUCE="$DAW/build-macos-arm64/_deps/juce-src"
PATCH="$ROOT/patches/tdpsola-direct-wet-diagnostic.patch"
TMP="/private/tmp/vibe-legal-adjacency-direct-wet-$RANDOM"
BUILD="$TMP/build"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT="$ROOT/artifacts/legal-adjacency-direct-wet-$STAMP"

for f in "$SOURCE/CMakeLists.txt" "$SOURCE/VibeAutotune/CausalTDPSOLARenderer.h" "$SOURCE/tests/TDPSOLARendererTest.cpp" "$RAW" "$RUNNER" "$JUCE/CMakeLists.txt" "$PATCH"; do
  [[ -e "$f" ]] || { print -u2 "Missing: $f"; exit 66; }
done
mkdir -p "$TMP" "$OUT/vibe"
cp "$SOURCE/CMakeLists.txt" "$TMP/CMakeLists.txt"
ditto "$SOURCE/VibeAutotune" "$TMP/VibeAutotune"
ditto "$SOURCE/tests" "$TMP/tests"
(cd "$TMP" && patch -p1 < "$PATCH")

flags='-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=1024 -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=128 -DVIBE_TENOR_ANALYSIS_HOP_SAMPLES=128 -DVIBE_HARD_LOCK_RENDERER_CROSSING_TRANSITION_MS=24.0 -DVIBE_RESEARCH_HARDTUNE_DOWNWARD_DWELL_FRAMES=0 -DVIBE_RESEARCH_LEGAL_SCALE_ADJACENCY=1 -DVIBE_TDPSOLA_DIAGNOSTIC_DIRECT_WET=1'
cmake -S "$TMP" -B "$BUILD" -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release \
  -DVIBE_JUCE_SOURCE_DIR:PATH="$JUCE" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$SOURCE/.third_party/signalsmith_linear-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$SOURCE/.third_party/signalsmith_stretch-src" \
  -DCMAKE_CXX_FLAGS:STRING="$flags" | tee "$OUT/configure.log"
cmake --build "$BUILD" --target VibeAutotune_VST3 --parallel 4 | tee "$OUT/build.log"
VST="$BUILD/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
[[ -d "$VST" ]] || { print -u2 'Diagnostic VST3 was not produced.'; exit 67; }
env STUDIOFORGE_CALIBRATION_VOICE=Alto STUDIOFORGE_CALIBRATION_KEY='F#' STUDIOFORGE_CALIBRATION_SCALE='Natural Minor' \
  "$RUNNER" "$RAW" "$OUT/vibe" VibeAutotune "$VST" | tee "$OUT/host-runner.log"
print "DIRECT-WET FORENSIC COMPLETE (not installed): $OUT"
print "Listen: $OUT/vibe/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav"
