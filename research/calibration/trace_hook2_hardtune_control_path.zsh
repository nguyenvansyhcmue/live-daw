#!/bin/zsh
# Read-only diagnostic render of the current exact Alto/F# Natural Minor 0-ms
# hard-tune path. It does not install, sign, or replace any plug-in.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
BUILD="${VIBE_BUILD:-$VIBE_ROOT/build-studioforge-juce8-stable}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
DIAGNOSTIC="$BUILD/VibeAutotuneSignalChainDiagnostic"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-hardtune-control-path-$(date +%Y%m%d-%H%M%S)"
PATCH="/Users/hiimdrdey/autotune/signal_chain_diagnostic_juce7_writer_compat.patch"

[[ -f "$RAW" ]] || { print -u2 "Missing source WAV: $RAW"; exit 2; }
cd "$VIBE_ROOT"
if ! git apply --reverse --check "$PATCH" >/dev/null 2>&1; then
  git apply "$PATCH"
fi
cmake --build "$BUILD" --target VibeAutotuneSignalChainDiagnostic --parallel 1
[[ -x "$DIAGNOSTIC" ]] || { print -u2 "Diagnostic executable missing: $DIAGNOSTIC"; exit 2; }

mkdir -p "$OUT"
# Classic off, Formant on, Retune/Flex/Humanize/Natural = 0, F# Natural Minor,
# Alto, Tracking 50. The final 1 selects the currently production spectral path.
VIBE_RAPID_ADJACENT_SELECTOR=1 "$DIAGNOSTIC" "$RAW" "$OUT" \
  0 1 0 0 0 0 1 0 0 0 0 - 1 > "$OUT/runner.log"
python3 /Users/hiimdrdey/autotune/analyze_hardtune_control_path.py "$OUT/full_default_intervals.csv"

print ""
print "TRACE COMPLETE (not installed): $OUT"
print "Read: $OUT/hard-tune-control-path.md"
