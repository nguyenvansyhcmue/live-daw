#!/bin/zsh
# Release gate for the exact causal TD-PSOLA + 24 ms crossing candidate.
# It is diagnostic only: it neither signs nor installs AU/VST3.
set -euo pipefail

root="/Users/hiimdrdey/autotune"
vibe_root="/Users/hiimdrdey/code/daw/autotune"
daw_root="/Users/hiimdrdey/code/daw"
build="${VIBE_CROSSING24_BUILD:-${vibe_root}/build-hook2-tdpsola-crossing-24}"
raw="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
juce="${daw_root}/build-macos-arm64/_deps/juce-src"
linear="${vibe_root}/.third_party/signalsmith_linear-src"
stretch="${vibe_root}/.third_party/signalsmith_stretch-src"
stamp="$(date +%Y%m%d-%H%M%S)"
out="${root}/artifacts/tdpsola-crossing24-release-gate-${stamp}"

for item in "$raw" "$juce/CMakeLists.txt" "$linear/CMakeLists.txt" "$stretch/CMakeLists.txt"; do
  [[ -e "$item" ]] || { print -u2 "Missing required input: $item"; exit 66; }
done

flags='-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_RAPID_ADJACENT_EVIDENCE_WINDOW_FRAMES=8 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=1024 -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=128 -DVIBE_HARD_LOCK_RENDERER_CROSSING_TRANSITION_MS=24.0'
mkdir -p "$out"

cmake -S "$vibe_root" -B "$build" -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release \
  -DVIBE_JUCE_SOURCE_DIR:PATH="$juce" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$linear" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$stretch" \
  -DCMAKE_CXX_FLAGS:STRING="$flags" | tee "$out/configure.log"

targets=(
  VibeAutotune_VST3
  VibeAutotuneCausalTDPSOLATest
  VibeAutotuneRendererStepResponse
  VibeAutotuneRealtimeSchedulerBenchmark
  VibeAutotuneCorrectionTrajectoryTest
  VibeAutotuneLiveControlPipelineTest
  VibeAutotuneControlHandoffTest
)
cmake --build "$build" --target "${targets[@]}" --parallel 4 | tee "$out/build.log"

"$build/VibeAutotuneCausalTDPSOLATest" | tee "$out/causal-safety.log"
"$build/VibeAutotuneRendererStepResponse" | tee "$out/renderer-step.log"
"$build/VibeAutotuneCorrectionTrajectoryTest" | tee "$out/trajectory.log"
"$build/VibeAutotuneLiveControlPipelineTest" | tee "$out/live-control.log"
"$build/VibeAutotuneControlHandoffTest" | tee "$out/control-handoff.log"

for host_block in 32 64 128; do
  "$build/VibeAutotuneRealtimeSchedulerBenchmark" "$raw" 4 "$host_block" \
    | tee "$out/realtime-tdpsola-host-${host_block}.log"
done

python3 - "$out" <<'PY'
import re
import sys
from pathlib import Path

out = Path(sys.argv[1])
lines = []
all_within = True
for block in (32, 64, 128):
    content = (out / f"realtime-tdpsola-host-{block}.log").read_text()
    match = re.search(r"^benchmark .*", content, re.MULTILINE)
    if not match:
        raise SystemExit(f"Missing benchmark result for block {block}")
    fields = dict(re.findall(r"(\w+)=([^\s]+)", match.group()))
    if fields.get("safety") != "PASS":
        raise SystemExit(f"Benchmark safety check failed for block {block}")
    max_us = float(fields["max_us"])
    deadline = float(fields["deadline_us"])
    within = max_us <= deadline
    all_within &= within
    lines.append(f"{block}: max {max_us:.3f} us / deadline {deadline:.3f} us; "
                 + ("within measured deadline" if within else "DEADLINE EXCEEDED"))
lines.append("Result: " + ("no deadline exceedance observed in this limited run"
                           if all_within else "NOT QUALIFIED FOR LIVE: deadline exceedance observed"))
lines.append("Even a clean offline run is not a real-device live qualification.")
(out / "deadline-summary.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
PY

print ''
print "DIAGNOSTICS COMPLETE (not installed; not a release verdict): $out"
print "Read: $out/deadline-summary.txt"
