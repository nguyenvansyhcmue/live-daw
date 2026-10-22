#!/bin/zsh
# Direct diagnostic of target-to-renderer correction delivery for the qualified
# fast-musical rail candidate. It never installs a VST3.
set -euo pipefail
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
BUILD="${VIBE_FAST_MUSICAL_RAIL_BUILD:-$VIBE_ROOT/build-fast-musical-rail-240}"
DIAGNOSTIC="$BUILD/VibeAutotuneSignalChainDiagnostic"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-fast-musical-delivery-$STAMP"
[[ -f "$RAW" ]] || { print -u2 "Missing source WAV: $RAW"; exit 2; }
cd "$VIBE_ROOT"
SOURCE="$VIBE_ROOT/VibeAutotune/CorrectionTrajectory.h"
rg -q 'VIBE_MUSICAL_RAIL_MAX_RETUNE_MS' "$SOURCE" || {
  print -u2 "Run the fast-musical candidate first; its source patch is required."; exit 65
}
cmake --build "$BUILD" --target VibeAutotuneSignalChainDiagnostic --parallel 1
[[ -x "$DIAGNOSTIC" ]] || { print -u2 "Diagnostic executable missing: $DIAGNOSTIC"; exit 2; }
mkdir -p "$OUT"
run_case() {
  local retune="$1"
  local destination="$OUT/retune_$retune"
  mkdir -p "$destination"
  "$DIAGNOSTIC" "$RAW" "$destination" 0 1 "$retune" 0 0 0 1 0 0 0 0 - 1 > "$destination/runner.log"
  awk -F, '
    NR == 1 { for (i=1; i<=NF; ++i) c[$i]=i; next }
    {
      d=$(c["deliveredRendererCorrectionCents"]);
      want=$(c["desiredCorrectionCents"]);
      wet=$(c["rendererShouldRenderWet"]);
      if (d != "" && d == d) {
        n++; if (d < 0) a=-d; else a=d;
        if (a > maxAbs) maxAbs=a;
        if (a >= 119.9) oldRail++;
        if (a >= 239.9) wideRail++;
        e=want-d; if (e < 0) e=-e; sumAbsError+=e;
      }
      if ($(c["targetChanged"]) == 1) commits++;
      if (wet == 1) wetFrames++;
      frames++;
    }
    END {
      printf "retune_ms=%s,frames=%d,wet_frames=%d,target_commits=%d,max_abs_delivered_cents=%.3f,at_or_above_120=%d,at_or_above_240=%d,mean_abs_desired_minus_delivered=%.3f\n",
             retune, frames, wetFrames, commits, maxAbs, oldRail, wideRail, n ? sumAbsError/n : 0;
    }' retune="$retune" "$destination/full_default_intervals.csv" > "$destination/delivery-summary.txt"
}
for retune in 0 10 25 50 100; do run_case "$retune"; done
cat "$OUT"/retune_*/delivery-summary.txt | tee "$OUT/delivery-summary.txt"
print "TRACE COMPLETE (not installed): $OUT"
print "Summary: $OUT/delivery-summary.txt"
