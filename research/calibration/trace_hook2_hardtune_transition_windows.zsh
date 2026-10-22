#!/bin/zsh
# Forensic, read-only trace of the two repeatable Hook-2 hard-tune outliers.
set -euo pipefail
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
BUILD="${VIBE_FAST_MUSICAL_RAIL_BUILD:-$VIBE_ROOT/build-fast-musical-rail-240}"
DIAGNOSTIC="$BUILD/VibeAutotuneSignalChainDiagnostic"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-hardtune-transition-windows-$STAMP"
[[ -f "$RAW" && -x "$DIAGNOSTIC" ]] || { print -u2 "Missing input or diagnostic binary."; exit 2; }
mkdir -p "$OUT"
"$DIAGNOSTIC" "$RAW" "$OUT" 0 1 0 0 0 0 1 0 0 0 0 - 1 > "$OUT/runner.log"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 /Users/hiimdrdey/autotune/analyze_hook2_selector_delivery.py "$OUT" > "$OUT/delivery-analyser.log"
awk -F, '
  NR == 1 { for (i=1;i<=NF;i++) c[$i]=i; print "time_ms,target_changed,target,candidate,desired_ct,retune_ct,transition_ms,source_timestamp,renderer_timestamp,spawn_target"; next }
  {
    t=$(c["timeMs"]);
    inWindow=(t >= 3550 && t <= 3820) || (t >= 4400 && t <= 4890);
    if (inWindow && ($(c["targetChanged"]) == 1 || int(t*10)%20 == 0))
      print t,$(c["targetChanged"]),$(c["committedTargetMidi"]),$(c["selectorCandidate"]),$(c["desiredCorrectionCents"]),$(c["retuneCorrectionCents"]),$(c["trajectoryTransitionDurationMs"]),$(c["sourceControlTimestamp"]),$(c["rendererControlTimestamp"]),$(c["spawnTargetMidi"]);
  }' OFS=, "$OUT/full_default_intervals.csv" > "$OUT/window-control-trace.csv"
print "TRACE COMPLETE (not installed): $OUT"
print "Windows: $OUT/window-control-trace.csv"
print "Delivery: $OUT/selector-delivery-summary.md"
