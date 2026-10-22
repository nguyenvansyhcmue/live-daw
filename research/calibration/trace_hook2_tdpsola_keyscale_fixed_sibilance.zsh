#!/bin/zsh
# Read-only TD-PSOLA sibilance provenance for the exact preview-on baseline.
# No plug-in is installed, signed, or modified.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
BUILD="${VIBE_KEY_SCALE_FIXED_BUILD:-$VIBE_ROOT/build-hook2-tdpsola-keyscale-fixed}"
DIAGNOSTIC="$BUILD/VibeAutotuneSignalChainDiagnostic"
PATCH="$ROOT/signal_chain_diagnostic_juce7_writer_compat.patch"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$ROOT/artifacts/hook2-tdpsola-keyscale-fixed-sibilance-$STAMP"

[[ -f "$RAW" ]] || { print -u2 "Missing Hook-2 WAV: $RAW"; exit 2; }
cd "$VIBE_ROOT"
if ! git apply --reverse --check "$PATCH" >/dev/null 2>&1; then git apply "$PATCH"; fi
cmake --build "$BUILD" --target VibeAutotuneSignalChainDiagnostic --parallel 1
[[ -x "$DIAGNOSTIC" ]] || { print -u2 "Diagnostic executable missing: $DIAGNOSTIC"; exit 2; }

mkdir -p "$OUT"
VIBE_RAPID_ADJACENT_SELECTOR=1 "$DIAGNOSTIC" "$RAW" "$OUT" \
  0 1 0 0 0 0 0 0 0 0 0 - 1 > "$OUT/runner.log"

awk -F, '
  NR == 1 {
    for (i = 1; i <= NF; ++i) c[$i] = i;
    print "time_ms,voiced,confidence,raw_f0,stable_f0,target,desired_ct,delivered_ct,dry_wet,sibilance_mix,high_frequency_evidence,periodic_coherence,artifact_dry_veto,grain_starved,should_render_wet,safety_dry_samples";
    next
  }
  {
    t = $(c["timeMs"]);
    inWindow = (t >= 6400 && t <= 6860) || (t >= 6920 && t <= 7160) || \
               (t >= 7540 && t <= 7770) || (t >= 8620 && t <= 8850);
    if (inWindow && int(t / 5) != int(last / 5))
      print t,$(c["voiced"]),$(c["pitchConfidence"]),$(c["rawF0"]),$(c["stableF0"]),$(c["committedTargetMidi"]),$(c["desiredCorrectionCents"]),$(c["deliveredRendererCorrectionCents"]),$(c["dryWetMix"]),$(c["sibilanceResidualMix"]),$(c["rendererHighFrequencyEvidence"]),$(c["rendererPeriodicCoherence"]),$(c["rendererArtifactDryVeto"]),$(c["rendererGrainStarved"]),$(c["rendererShouldRenderWet"]),$(c["rendererSafetyDrySamples"]);
    last = t;
  }' OFS=, "$OUT/full_default_intervals.csv" > "$OUT/sibilance-control-windows.csv"

print ''
print "TRACE COMPLETE (diagnostic only; not installed): $OUT"
print "Windows: $OUT/sibilance-control-windows.csv"
