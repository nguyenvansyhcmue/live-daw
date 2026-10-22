#!/bin/zsh
# Qualification gate for the measured 24 ms renderer-crossing candidate.
# It builds/runs tests only. It does not copy, sign, or install any plugin.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
BUILD="${VIBE_CROSSING24_BUILD:-$VIBE_ROOT/build-hook2-tdpsola-crossing-24}"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-tdpsola-crossing24-qualification-$(date +%Y%m%d-%H%M%S)"

[[ -f "$BUILD/CMakeCache.txt" ]] || { print -u2 "Missing crossing-24 build: $BUILD"; exit 66; }
rg -q 'VIBE_HARD_LOCK_RENDERER_CROSSING_TRANSITION_MS=24\.0' "$BUILD/CMakeCache.txt" || {
  print -u2 'Build is not the exact 24 ms candidate; run the crossing sweep first.'
  exit 65
}
mkdir -p "$OUT"

targets=(
  VibeAutotuneCorrectionTrajectoryTest
  VibeAutotuneLiveControlPipelineTest
  VibeAutotuneCausalTDPSOLATest
  VibeAutotuneNotePolicyTest
  VibeAutotuneKeyScaleLivePathTest
  VibeAutotuneControlHandoffTest
)

cmake --build "$BUILD" --target "${targets[@]}" --parallel 4 | tee "$OUT/build.log"
for target in "${targets[@]}"; do
  print "=== $target ===" | tee -a "$OUT/tests.log"
  "$BUILD/$target" 2>&1 | tee -a "$OUT/tests.log"
done

print ''
print "QUALIFICATION PASS (not installed): $OUT"
print "Read: $OUT/tests.log"
