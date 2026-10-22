#!/bin/zsh
# Read-only forensic trace for the current TD-PSOLA hard-tune candidate.
# It never builds or installs a plug-in bundle; it only builds the diagnostic.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
BUILD="${VIBE_TDPSOLA_TRACE_BUILD:-$VIBE_ROOT/build-hardtune-tdpsola-rail160}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
DIAGNOSTIC="$BUILD/VibeAutotuneSignalChainDiagnostic"
PATCH="/Users/hiimdrdey/autotune/signal_chain_diagnostic_juce7_writer_compat.patch"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-tdpsola-transition-windows-$(date +%Y%m%d-%H%M%S)"

[[ -f "$RAW" ]] || { print -u2 "Missing source WAV: $RAW"; exit 2; }
cd "$VIBE_ROOT"
if ! git apply --reverse --check "$PATCH" >/dev/null 2>&1; then git apply "$PATCH"; fi
cmake --build "$BUILD" --target VibeAutotuneSignalChainDiagnostic --parallel 1
[[ -x "$DIAGNOSTIC" ]] || { print -u2 "Diagnostic executable missing: $DIAGNOSTIC"; exit 2; }
mkdir -p "$OUT"

# Classic off, Formant on, Retune/Flex/Humanize/Natural 0, F# Natural Minor,
# Alto, Tracking 50. Argument 9 is explicitly 0: causal TD-PSOLA.
VIBE_RAPID_ADJACENT_SELECTOR=1 "$DIAGNOSTIC" "$RAW" "$OUT" \
  0 1 0 0 0 0 0 0 0 0 0 - 1 > "$OUT/runner.log"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 /Users/hiimdrdey/autotune/analyze_hook2_selector_delivery.py "$OUT" > "$OUT/delivery-analyser.log"
awk -F, '
  NR == 1 { for (i=1;i<=NF;i++) c[$i]=i;
            print "time_ms,target_changed,target_before,previous_target,target,candidate,selector_decision,frames_since_commit,raw_f0,stable_f0,raw_midi,confidence,decision_excess_ct,hysteresis_ct,rapid_candidate,rapid_evidence,preview_direction,preview_note,preview_frames,preview_travel_ct,desired_ct,retune_ct,transition_ms,crossing_active,crossing_target,crossing_progress,excursion_active,excursion_phase,active,delivered_ct,source_timestamp,renderer_timestamp,spawn_target"; next }
  { t=$(c["timeMs"]); inWindow=(t >= 3550 && t <= 3820) || (t >= 4400 && t <= 4890) || (t >= 6750 && t <= 7200);
    if (inWindow && ($(c["targetChanged"]) == 1 || int(t*10)%20 == 0))
      print t,$(c["targetChanged"]),$(c["selectorCurrentTargetBefore"]),$(c["selectorPreviousTarget"]),$(c["committedTargetMidi"]),$(c["selectorCandidate"]),$(c["selectorDecision"]),$(c["selectorFramesSinceCommit"]),$(c["rawF0"]),$(c["stableF0"]),$(c["rawMidi"]),$(c["pitchConfidence"]),$(c["targetDecisionExcessCents"]),$(c["targetHysteresisCents"]),$(c["rapidAdjacentCandidateMidi"]),$(c["rapidAdjacentEvidenceFrames"]),$(c["trajectoryPreviewDirection"]),$(c["trajectoryPreviewNote"]),$(c["trajectoryPreviewUpdates"]),$(c["trajectoryPreviewTravelCents"]),$(c["desiredCorrectionCents"]),$(c["retuneCorrectionCents"]),$(c["trajectoryTransitionDurationMs"]),$(c["trajectoryRendererCrossingActive"]),$(c["trajectoryRendererCrossingTargetMidi"]),$(c["trajectoryRendererCrossingProgress"]),$(c["trajectoryExcursionActive"]),$(c["trajectoryExcursionPhase"]),$(c["correctionIsActive"]),$(c["deliveredRendererCorrectionCents"]),$(c["sourceControlTimestamp"]),$(c["rendererControlTimestamp"]),$(c["spawnTargetMidi"])
  }' OFS=, "$OUT/full_default_intervals.csv" > "$OUT/window-control-trace.csv"

print ""
print "TRACE COMPLETE (not installed; TD-PSOLA): $OUT"
print "Windows:  $OUT/window-control-trace.csv"
print "Delivery: $OUT/selector-delivery-summary.md"
