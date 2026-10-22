#!/bin/zsh
# Qualification only: does not switch the production renderer or install VST3.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
BUILD="${VIBE_BUILD:-$VIBE_ROOT/build-studioforge-juce8-stable}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/tdpsola-live-qualification-$STAMP"
mkdir -p "$OUT"
BUILD_LOG="$OUT/build.log"

cd "$VIBE_ROOT"
for PATCH in \
  /Users/hiimdrdey/autotune/tdpsola_realtime_candidate_benchmark.patch \
  /Users/hiimdrdey/autotune/tdpsola_realtime_deadline_accounting.patch; do
  if git apply --reverse --check "$PATCH" >/dev/null 2>&1; then
    print "Already applied: ${PATCH:t}"
  else
    git apply "$PATCH"
    print "Applied: ${PATCH:t}"
  fi
done
if ! cmake --build "$BUILD" --parallel 1 --target \
  VibeAutotuneCausalTDPSOLATest \
  VibeAutotuneRendererStepResponse \
  VibeAutotuneRealtimeSchedulerBenchmark 2>&1 | tee "$BUILD_LOG"; then
  print -u2 "BUILD FAILED. Full compiler log: $BUILD_LOG"
  exit 1
fi

"$BUILD/VibeAutotuneCausalTDPSOLATest" | tee "$OUT/causal-safety.log"
"$BUILD/VibeAutotuneRendererStepResponse" | tee "$OUT/renderer-step.log"

if [[ -f "$RAW" ]]; then
  # Compare the shipped spectral path with the causal candidate. Both are
  # diagnostic-only; this script neither changes renderer defaults nor installs.
  for block in 32 64 128; do
    "$BUILD/VibeAutotuneRealtimeSchedulerBenchmark" "$RAW" 3 "$block" \
      | tee "$OUT/realtime-$block.log"
    "$BUILD/VibeAutotuneRealtimeSchedulerBenchmark" "$RAW" 4 "$block" \
      | tee "$OUT/tdpsola-candidate-$block.log"
  done
fi

print ""
print "QUALIFICATION RUN COMPLETE (not a production-promotion verdict): $OUT"
