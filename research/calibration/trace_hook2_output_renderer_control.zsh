#!/bin/zsh
# Diagnostic-only provenance trace. No plugin bundle is installed or signed.
set -euo pipefail
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
ROOT="/Users/hiimdrdey/autotune"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
JUCE="$DAW_ROOT/build-macos-arm64/_deps/juce-src"
LINEAR="$VIBE_ROOT/.third_party/signalsmith_linear-src"
STRETCH="$VIBE_ROOT/.third_party/signalsmith_stretch-src"
OUT="$ROOT/artifacts/hook2-output-renderer-control-$(date +%Y%m%d-%H%M%S)"
BUILD="$VIBE_ROOT/build-hook2-output-renderer-control"
ALTO_FRAME="${VIBE_ALTO_FRAME:-2048}"
ALTO_HOP="${VIBE_ALTO_HOP:-256}"
[[ "$ALTO_FRAME" == <-> && "$ALTO_HOP" == <-> ]] || { print -u2 'VIBE_ALTO_FRAME and VIBE_ALTO_HOP must be positive integers.'; exit 2; }
for f in "$RAW" "$JUCE/CMakeLists.txt" "$LINEAR/CMakeLists.txt" "$STRETCH/CMakeLists.txt"; do [[ -f "$f" ]] || { print -u2 "Missing: $f"; exit 2; }; done
rg -q 'outputRendererControlTimestamp' "$VIBE_ROOT/VibeAutotune/PluginProcessor.h" || { print -u2 'Run add_output_renderer_control_trace.zsh first.'; exit 3; }
cmake -S "$VIBE_ROOT" -B "$BUILD" -DCMAKE_BUILD_TYPE=Release \
  -DVIBE_JUCE_SOURCE_DIR:PATH="$JUCE" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$LINEAR" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$STRETCH" \
  -DCMAKE_CXX_FLAGS:STRING="-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_RAPID_ADJACENT_EVIDENCE_WINDOW_FRAMES=8 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=$ALTO_FRAME -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=$ALTO_HOP" >/dev/null
cmake --build "$BUILD" --target VibeAutotuneSignalChainDiagnostic --parallel 1
mkdir -p "$OUT"
VIBE_RAPID_ADJACENT_SELECTOR=1 "$BUILD/VibeAutotuneSignalChainDiagnostic" "$RAW" "$OUT" 0 1 0 0 0 0 0 0 0 0 0 - 1 > "$OUT/runner.log"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ROOT/audit_output_renderer_control.py" "$OUT/full_default_intervals.csv" "$OUT/provenance" >/dev/null
printf '\nTRACE COMPLETE (diagnostic only; not installed): %s\n' "$OUT"
printf 'Alto analysis: %s frame / %s hop\n' "$ALTO_FRAME" "$ALTO_HOP"
printf 'Read first: %s/provenance/output-renderer-control-report.md\n' "$OUT"
