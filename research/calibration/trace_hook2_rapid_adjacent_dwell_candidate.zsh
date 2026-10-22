#!/bin/zsh
# Trace the existing selector-to-renderer pipeline for one dwell candidate.
# This is diagnostic only and does not install a plug-in.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
DWELL_SAMPLES="${VIBE_RAPID_ADJACENT_DWELL_SAMPLES:-768}"
STEREO_HOST="${VIBE_DIAGNOSTIC_STEREO_HOST:-1}"
[[ "$DWELL_SAMPLES" == <-> && "$DWELL_SAMPLES" -ge 256 && "$DWELL_SAMPLES" -le 3840 ]] || {
  print -u2 "VIBE_RAPID_ADJACENT_DWELL_SAMPLES must be an integer from 256 to 3840."
  exit 64
}
[[ "$STEREO_HOST" == "0" || "$STEREO_HOST" == "1" ]] || {
  print -u2 "VIBE_DIAGNOSTIC_STEREO_HOST must be 0 (direct mono) or 1 (StudioForge-style stereo)."
  exit 64
}
BUILD="${VIBE_RAPID_ADJACENT_TRACE_BUILD:-$VIBE_ROOT/build-rapid-adjacent-dwell-$DWELL_SAMPLES}"
PATCH="/Users/hiimdrdey/autotune/vibe-rapid-adjacent-dwell-config.patch"
COMPAT_PATCH="/Users/hiimdrdey/autotune/signal_chain_diagnostic_juce7_writer_compat.patch"
HOST_PARITY_PATCH="/Users/hiimdrdey/autotune/signal_chain_diagnostic_stereo_host_parity.patch"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-rapid-adjacent-trace-dwell${DWELL_SAMPLES}-$STAMP"

[[ -f "$RAW" ]] || { print -u2 "Missing source WAV: $RAW"; exit 66; }

cd "$VIBE_ROOT"
if ! git apply --reverse --check "$PATCH" >/dev/null 2>&1; then
  git apply "$PATCH"
fi
if ! git apply --reverse --check "$COMPAT_PATCH" >/dev/null 2>&1; then
  git apply "$COMPAT_PATCH"
fi
if ! git apply --reverse --check "$HOST_PARITY_PATCH" >/dev/null 2>&1; then
  git apply "$HOST_PARITY_PATCH"
fi

cmake -S "$VIBE_ROOT" -B "$BUILD" -G "Unix Makefiles" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="-DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=$DWELL_SAMPLES" \
  -DVIBE_JUCE_SOURCE_DIR="$DAW_ROOT/build-macos-arm64/_deps/juce-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR="$VIBE_ROOT/.third_party/signalsmith_linear-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH="$VIBE_ROOT/.third_party/signalsmith_stretch-src"
cmake --build "$BUILD" --target VibeAutotuneSignalChainDiagnostic --parallel 1

DIAGNOSTIC="$BUILD/VibeAutotuneSignalChainDiagnostic"
[[ -x "$DIAGNOSTIC" ]] || { print -u2 "Missing diagnostic executable: $DIAGNOSTIC"; exit 1; }
CASE="$OUT/hard_tune_natural_0"
mkdir -p "$CASE"
VIBE_RAPID_ADJACENT_SELECTOR=1 VIBE_DIAGNOSTIC_STEREO_HOST="$STEREO_HOST" "$DIAGNOSTIC" "$RAW" "$CASE" \
  0 1 0 0 0 0 1 0 0 0 0 - 1 > "$CASE/runner.log"

awk -F, '
  NR == 1 { for (i=1; i<=NF; ++i) col[$i]=i; next }
  {
    decision=$(col["selectorDecision"]); decisions[decision]++;
    if ($(col["targetChanged"]) == 1)
      printf "commit,time_ms=%.3f,target=%s,candidate=%s,raw_midi=%s,decision=%s,pending=%s,excess_ct=%.2f\\n", \
        $(col["timeMs"]), $(col["committedTargetMidi"]), $(col["selectorCandidate"]), \
        $(col["rawMidi"]), decision, $(col["pendingTargetFrames"]), $(col["targetDecisionExcessCents"]);
  }
  END { printf "decision_counts"; for (i=0; i<=6; ++i) printf ",%d=%d", i, decisions[i]+0; print ""; }
' "$CASE/full_default_intervals.csv" > "$CASE/selector-summary.txt"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
python3 /Users/hiimdrdey/autotune/analyze_hook2_selector_delivery.py "$CASE"

print ""
print "TRACE COMPLETE (not installed; stereo-host=$STEREO_HOST): $OUT"
print "Selector: $CASE/selector-summary.txt"
print "Delivery: $CASE/selector-delivery-summary.md"
