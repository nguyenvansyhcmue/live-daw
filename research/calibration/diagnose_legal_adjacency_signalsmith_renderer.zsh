#!/bin/zsh
# Diagnostic only. Compares the candidate's alternative phase-continuous
# Signalsmith renderer against Artist while preserving detector, target policy,
# key/scale, and all user controls. Nothing is installed or signed.
set -euo pipefail

ROOT='/Users/hiimdrdey/autotune'
DAW='/Users/hiimdrdey/code/daw'
SOURCE="$ROOT/artifacts/crossing24-bounded-preview-20261017-113341/source"
RAW='/Users/hiimdrdey/Music/Music/Media.localized/Music/Unknown Artist/Unknown Album/hook2_raw_segment.wav'
ARTIST="$ROOT/artifacts/crossing24-bounded-preview-20261017-113218/source/renders/target-autotune-artist.wav"
TOOLS="$ROOT/artifacts/crossing24-bounded-preview-20261017-113218/source/tools"
RUNNER="$DAW/build-calibration-arm64/StudioForgeCalibrationRunner"
JUCE="$DAW/build-macos-arm64/_deps/juce-src"
BUILD="/private/tmp/vibe-legal-adjacency-signalsmith-$RANDOM"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT="$ROOT/artifacts/legal-adjacency-signalsmith-$STAMP"

expected_raw='c241b07c23528541960b45ca4889a1ae105200ab9ba1a4a239c81683f98bac28'
expected_artist='fe8fcafac41f18fe7c5b823e52bf94b988fcf1a0270e93722bfe4db5a21caadb'

for item in "$SOURCE/CMakeLists.txt" "$RAW" "$ARTIST" "$RUNNER" "$JUCE/CMakeLists.txt" \
            "$SOURCE/.third_party/signalsmith_linear-src/CMakeLists.txt" \
            "$SOURCE/.third_party/signalsmith_stretch-src/CMakeLists.txt"; do
  [[ -e "$item" ]] || { print -u2 "Missing required input: $item"; exit 66; }
done
[[ "$(shasum -a 256 "$RAW" | awk '{print $1}')" == "$expected_raw" ]] || { print -u2 'Raw checksum mismatch.'; exit 65; }
[[ "$(shasum -a 256 "$ARTIST" | awk '{print $1}')" == "$expected_artist" ]] || { print -u2 'Artist checksum mismatch.'; exit 65; }

# Exact approved control policy, but the TD-PSOLA candidate switch is off.
# This changes only the synthesis engine; it is not a knob/preset experiment.
flags='-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=0 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=1024 -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=128 -DVIBE_TENOR_ANALYSIS_HOP_SAMPLES=128 -DVIBE_HARD_LOCK_RENDERER_CROSSING_TRANSITION_MS=24.0 -DVIBE_RESEARCH_HARDTUNE_DOWNWARD_DWELL_FRAMES=0 -DVIBE_RESEARCH_LEGAL_SCALE_ADJACENCY=1'

mkdir -p "$OUT/vibe"
cmake -S "$SOURCE" -B "$BUILD" -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release \
  -DVIBE_JUCE_SOURCE_DIR:PATH="$JUCE" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$SOURCE/.third_party/signalsmith_linear-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$SOURCE/.third_party/signalsmith_stretch-src" \
  -DCMAKE_CXX_FLAGS:STRING="$flags" | tee "$OUT/configure.log"
cmake --build "$BUILD" --target VibeAutotune_VST3 --parallel 4 | tee "$OUT/build.log"

VST="$BUILD/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
[[ -d "$VST" ]] || { print -u2 'Diagnostic VST3 was not produced.'; exit 67; }
env STUDIOFORGE_CALIBRATION_VOICE=Alto STUDIOFORGE_CALIBRATION_KEY='F#' STUDIOFORGE_CALIBRATION_SCALE='Natural Minor' \
  "$RUNNER" "$RAW" "$OUT/vibe" VibeAutotune "$VST" | tee "$OUT/host-runner.log"

VIBE_WAV="$OUT/vibe/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav"
[[ -f "$VIBE_WAV" ]] || { print -u2 'Hard-tune bounce missing.'; exit 68; }
printf 'case,retune_ms,flex_tune,humanize,natural_vibrato,output\n0,0,0,0,0,"%s"\n' "$VIBE_WAV" > "$OUT/vibe.csv"
printf 'case,retune_ms,flex_tune,humanize,natural_vibrato,output\n0,0,0,0,0,"%s"\n' "$ARTIST" > "$OUT/artist.csv"
PYTHONPATH="$TOOLS${PYTHONPATH:+:$PYTHONPATH}" python3 "$DAW/Tools/analyze_studioforge_calibration.py" \
  "$RAW" "$OUT/vibe.csv" "$OUT/artist.csv" "$OUT/comparison"
python3 "$ROOT/tools/diagnose_vocal_texture_ab.py" --raw "$RAW" --artist "$ARTIST" \
  --candidate "$VIBE_WAV" --label signalsmith --output "$OUT/texture-report"
printf '%s\n' '# Phase-continuous renderer A/B' '' \
  '- Baseline control policy: exact 64e935 candidate.' \
  '- Sole changed variable: `VIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=0`.' \
  '- No plug-in installation, signing, or DAW packaging was performed.' > "$OUT/README.md"

print ''
print "SIGNALSMITH RENDERER A/B COMPLETE (not installed): $OUT"
print "Listen:  $VIBE_WAV"
print "Pitch:   $OUT/comparison/calibration-report.md"
print "Texture: $OUT/texture-report/signalsmith-texture.json"
