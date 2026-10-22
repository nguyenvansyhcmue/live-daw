#!/bin/zsh
# Read-only forensic trace for the exact candidate used by
# run_hook2_tdpsola_keyscale_fixed_host_ab.zsh.  It does not install or sign a plug-in.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
BUILD="${VIBE_KEY_SCALE_FIXED_BUILD:-$VIBE_ROOT/build-hook2-tdpsola-keyscale-fixed}"
DIAGNOSTIC="$BUILD/VibeAutotuneSignalChainDiagnostic"
PATCH="$ROOT/signal_chain_diagnostic_juce7_writer_compat.patch"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$ROOT/artifacts/hook2-tdpsola-keyscale-fixed-controls-$STAMP"

[[ -f "$RAW" ]] || { print -u2 "Missing Hook-2 WAV: $RAW"; exit 2; }

cd "$VIBE_ROOT"
if ! git apply --reverse --check "$PATCH" >/dev/null 2>&1; then
  git apply "$PATCH"
fi
cmake --build "$BUILD" --target VibeAutotuneSignalChainDiagnostic --parallel 1
[[ -x "$DIAGNOSTIC" ]] || { print -u2 "Diagnostic executable missing: $DIAGNOSTIC"; exit 2; }

mkdir -p "$OUT"
# Same sound-setting contract as the host A/B: Classic off, Formant on,
# Retune/Flex/Humanize/Natural 0, Alto, F# Natural Minor, Tracking 50.
# The final 0 selects the causal TD-PSOLA diagnostic path.
VIBE_RAPID_ADJACENT_SELECTOR=1 "$DIAGNOSTIC" "$RAW" "$OUT" \
  0 1 0 0 0 0 0 0 0 0 0 - 1 > "$OUT/runner.log"

PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
  python3 "$ROOT/analyze_hook2_selector_delivery.py" "$OUT" > "$OUT/delivery-analyser.log"

# These are the only windows currently worth changing: the worst Artist-vs-Vibe
# events from the host A/B.  Sampling every 20 ms keeps the evidence readable.
awk -F, '
  NR == 1 {
    for (i = 1; i <= NF; ++i) c[$i] = i;
    print "time_ms,target_changed,target_before,previous_target,target,candidate,decision,frames_since_commit,raw_f0,stable_f0,confidence,desired_ct,retune_ct,transition_ms,crossing_active,crossing_progress,delivered_ct,source_timestamp,output_renderer_timestamp,spawn_target";
    next
  }
  {
    t = $(c["timeMs"]);
    inWindow = (t >= 1450 && t <= 1760) || (t >= 3850 && t <= 4140) || \
               (t >= 4400 && t <= 4780) || (t >= 5850 && t <= 6170);
    if (inWindow && ($(c["targetChanged"]) == 1 || int(t / 20) != int(last / 20))) {
      print t,$(c["targetChanged"]),$(c["selectorCurrentTargetBefore"]),$(c["selectorPreviousTarget"]),$(c["committedTargetMidi"]),$(c["selectorCandidate"]),$(c["selectorDecision"]),$(c["selectorFramesSinceCommit"]),$(c["rawF0"]),$(c["stableF0"]),$(c["pitchConfidence"]),$(c["desiredCorrectionCents"]),$(c["retuneCorrectionCents"]),$(c["trajectoryTransitionDurationMs"]),$(c["trajectoryRendererCrossingActive"]),$(c["trajectoryRendererCrossingProgress"]),$(c["deliveredRendererCorrectionCents"]),$(c["sourceControlTimestamp"]),$(c["outputRendererControlTimestamp"]),$(c["spawnTargetMidi"]);
    }
    last = t;
  }' OFS=, "$OUT/full_default_intervals.csv" > "$OUT/focused-control-windows.csv"

print ''
print "TRACE COMPLETE (diagnostic only; not installed): $OUT"
print "Read first: $OUT/selector-delivery-summary.md"
print "Windows:    $OUT/focused-control-windows.csv"
