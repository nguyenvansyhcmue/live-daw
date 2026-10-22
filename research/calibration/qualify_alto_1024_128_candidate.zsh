#!/bin/zsh
# Regression qualification for the Alto 1024-frame / 128-hop candidate.
# This script does not edit, sign, or install the plug-in bundle.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
ROOT="/Users/hiimdrdey/autotune"
JUCE="$DAW_ROOT/build-macos-arm64/_deps/juce-src"
LINEAR="$VIBE_ROOT/.third_party/signalsmith_linear-src"
STRETCH="$VIBE_ROOT/.third_party/signalsmith_stretch-src"
BUILD="$VIBE_ROOT/build-alto-1024-128-qualification"
OUT="$ROOT/artifacts/alto-1024-128-qualification-$(date +%Y%m%d-%H%M%S)"

for item in "$VIBE_ROOT/CMakeLists.txt" "$JUCE/CMakeLists.txt" "$LINEAR/CMakeLists.txt" "$STRETCH/CMakeLists.txt"; do
  [[ -f "$item" ]] || { print -u2 "Missing required source: $item"; exit 2; }
done

flags="-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_RAPID_ADJACENT_EVIDENCE_WINDOW_FRAMES=8 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=1024 -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=128"
mkdir -p "$OUT"

cmake -S "$VIBE_ROOT" -B "$BUILD" -DCMAKE_BUILD_TYPE=Release \
  -DVIBE_JUCE_SOURCE_DIR:PATH="$JUCE" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$LINEAR" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$STRETCH" \
  -DCMAKE_CXX_FLAGS:STRING="$flags" | tee "$OUT/configure.log"

targets=(
  VibeAutotuneCorrectionTrajectoryTest
  VibeAutotuneControlHandoffTest
  VibeAutotuneNotePolicyTest
  VibeAutotuneKeyScaleLivePathTest
)

for target in $targets; do
  cmake --build "$BUILD" --target "$target" --parallel 1 | tee "$OUT/$target.build.log"
  "$BUILD/$target" | tee "$OUT/$target.run.log"
done

cat > "$OUT/qualification-summary.md" <<EOF
# Alto 1024 / 128 qualification

- Candidate only; no source defaults, installed VST3/AU, signature, or DAW package were changed.
- Configuration: Alto analysis frame 1024 samples; hop 128 samples.
- Passed executables: ${targets[*]}
- Next gate: repeat Hook-2 trace, compare output-aligned trajectory with the 2048/256 baseline, then promote only if the regression suite and A/B criteria remain green.

## Non-gating architecture finding

VibeAutotuneLiveControlPipelineTest is intentionally not a promotion gate for this detector candidate: its LiveControlPipeline is presently only included by test tools and is not called from PluginProcessor, the production plug-in audio path. Its glide test currently fails identically with and without the Alto 1024/128 macros (maximum ratio step 0.0119021). That duplicate harness must be either integrated with PluginProcessor or removed in a separate live-engine consolidation change; it must not be fixed by silently changing the production Retune law during this detector qualification.
EOF

print "\nQUALIFICATION PASSED (not installed): $OUT"
