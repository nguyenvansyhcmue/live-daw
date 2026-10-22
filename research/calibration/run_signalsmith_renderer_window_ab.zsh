#!/bin/zsh
# Usage: run_signalsmith_renderer_window_ab.zsh <window> <hop>
# One controlled renderer-window A/B. It never installs a binary.
set -euo pipefail
[[ $# -eq 2 ]] || { print -u2 'Usage: window hop'; exit 64; }
WINDOW=$1
HOP=$2
[[ "$WINDOW" == <-> && "$HOP" == <-> ]] || { print -u2 'Window/hop must be integers.'; exit 64; }

ROOT='/Users/hiimdrdey/autotune'
DAW='/Users/hiimdrdey/code/daw'
SOURCE="$ROOT/artifacts/crossing24-bounded-preview-20261017-113341/source"
RAW='/Users/hiimdrdey/Music/Music/Media.localized/Music/Unknown Artist/Unknown Album/hook2_raw_segment.wav'
ARTIST="$ROOT/artifacts/crossing24-bounded-preview-20261017-113218/source/renders/target-autotune-artist.wav"
TOOLS="$ROOT/artifacts/crossing24-bounded-preview-20261017-113218/source/tools"
RUNNER="$DAW/build-calibration-arm64/StudioForgeCalibrationRunner"
JUCE="$DAW/build-macos-arm64/_deps/juce-src"
BUILD="/private/tmp/vibe-signalsmith-w${WINDOW}-h${HOP}-$RANDOM"
OUT="$ROOT/artifacts/signalsmith-w${WINDOW}-h${HOP}-$(date +%Y%m%d-%H%M%S)"

for item in "$SOURCE/CMakeLists.txt" "$RAW" "$ARTIST" "$RUNNER" "$JUCE/CMakeLists.txt"; do
  [[ -e "$item" ]] || { print -u2 "Missing: $item"; exit 66; }
done
flags="-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=0 -DVIBE_SPECTRAL_WINDOW_SAMPLES=$WINDOW -DVIBE_SPECTRAL_HOP_SAMPLES=$HOP -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=1024 -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=128 -DVIBE_TENOR_ANALYSIS_HOP_SAMPLES=128 -DVIBE_HARD_LOCK_RENDERER_CROSSING_TRANSITION_MS=24.0 -DVIBE_RESEARCH_HARDTUNE_DOWNWARD_DWELL_FRAMES=0 -DVIBE_RESEARCH_LEGAL_SCALE_ADJACENCY=1"
mkdir -p "$OUT/vibe"
cmake -S "$SOURCE" -B "$BUILD" -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release \
  -DVIBE_JUCE_SOURCE_DIR:PATH="$JUCE" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$SOURCE/.third_party/signalsmith_linear-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$SOURCE/.third_party/signalsmith_stretch-src" \
  -DCMAKE_CXX_FLAGS:STRING="$flags"
cmake --build "$BUILD" --target VibeAutotune_VST3 --parallel 1
VST="$BUILD/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
env STUDIOFORGE_CALIBRATION_VOICE=Alto STUDIOFORGE_CALIBRATION_KEY='F#' STUDIOFORGE_CALIBRATION_SCALE='Natural Minor' \
 "$RUNNER" "$RAW" "$OUT/vibe" VibeAutotune "$VST"
VIBE="$OUT/vibe/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav"
printf 'case,retune_ms,flex_tune,humanize,natural_vibrato,output\n0,0,0,0,0,"%s"\n' "$VIBE" > "$OUT/vibe.csv"
printf 'case,retune_ms,flex_tune,humanize,natural_vibrato,output\n0,0,0,0,0,"%s"\n' "$ARTIST" > "$OUT/artist.csv"
PYTHONPATH="$TOOLS${PYTHONPATH:+:$PYTHONPATH}" python3 "$DAW/Tools/analyze_studioforge_calibration.py" "$RAW" "$OUT/vibe.csv" "$OUT/artist.csv" "$OUT/comparison"
python3 "$ROOT/tools/diagnose_vocal_texture_ab.py" --raw "$RAW" --artist "$ARTIST" --candidate "$VIBE" --label "signalsmith_w${WINDOW}_h${HOP}" --output "$OUT/texture-report.md"
print "WINDOW A/B COMPLETE (not installed): $OUT"
