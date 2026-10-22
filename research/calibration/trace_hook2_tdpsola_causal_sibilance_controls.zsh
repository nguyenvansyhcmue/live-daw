#!/bin/zsh
# Read-only provenance trace for the causal-sibilance A/B candidate.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
BUILD="${VIBE_CAUSAL_SIBILANCE_BUILD:-$VIBE_ROOT/build-hook2-tdpsola-causal-sibilance}"
DIAGNOSTIC="$BUILD/VibeAutotuneSignalChainDiagnostic"
PATCH="$ROOT/signal_chain_diagnostic_juce7_writer_compat.patch"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$ROOT/artifacts/hook2-tdpsola-causal-sibilance-controls-$STAMP"

[[ -f "$RAW" ]] || { print -u2 "Missing Hook-2 WAV: $RAW"; exit 2; }
cd "$VIBE_ROOT"
if ! git apply --reverse --check "$PATCH" >/dev/null 2>&1; then git apply "$PATCH"; fi
cmake --build "$BUILD" --target VibeAutotuneSignalChainDiagnostic --parallel 1
[[ -x "$DIAGNOSTIC" ]] || { print -u2 "Diagnostic executable missing: $DIAGNOSTIC"; exit 2; }
mkdir -p "$OUT"
VIBE_RAPID_ADJACENT_SELECTOR=1 "$DIAGNOSTIC" "$RAW" "$OUT" \
  0 1 0 0 0 0 0 0 0 0 0 - 1 > "$OUT/runner.log"

awk -F, '
  NR == 1 { for (i=1; i<=NF; ++i) c[$i]=i;
    print "time_ms,voiced,confidence,dry_wet,sibilance_mix,high_frequency_evidence,periodic_coherence,should_render_wet,grain_starved"; next }
  { t=$(c["timeMs"]); inWindow=(t>=6940 && t<=7080) || (t>=7580 && t<=7700) || (t>=8660 && t<=8800);
    if (inWindow && int(t/2)!=int(last/2))
      print t,$(c["voiced"]),$(c["pitchConfidence"]),$(c["dryWetMix"]),$(c["sibilanceResidualMix"]),$(c["rendererHighFrequencyEvidence"]),$(c["rendererPeriodicCoherence"]),$(c["rendererShouldRenderWet"]),$(c["rendererGrainStarved"]);
    last=t
  }' OFS=, "$OUT/full_default_intervals.csv" > "$OUT/sibilance-envelope-windows.csv"

print ''
print "TRACE COMPLETE (diagnostic only; not installed): $OUT"
print "Windows: $OUT/sibilance-envelope-windows.csv"
