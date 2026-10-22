#!/bin/zsh
# Verify the selector path in the already-built 64 ms reversal-guard candidate.
# This is read-only: it neither installs nor signs a plug-in.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
GUARD_MS="${VIBE_HARD_TUNE_RAPID_REVERSAL_GUARD_MS:-64}"
BUILD="${VIBE_REVERSAL_GUARD_BUILD:-$VIBE_ROOT/build-reversal-guard-$GUARD_MS}"
DIAGNOSTIC="$BUILD/VibeAutotuneSignalChainDiagnostic"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-reversal-guard${GUARD_MS}-selector-$STAMP"

[[ "$GUARD_MS" == <-> ]] || { print -u2 "Guard must be an integer millisecond value."; exit 64; }
[[ -f "$RAW" && -d "$BUILD" ]] || {
  print -u2 "Missing Hook-2 source WAV or candidate build: $BUILD"
  exit 66
}

# Refuse to claim that this is the 64 ms candidate if CMake did not retain
# the intended compile definition.
EXPECTED="-DVIBE_HARD_TUNE_RAPID_REVERSAL_GUARD_SECONDS=$(awk "BEGIN { print $GUARD_MS / 1000.0 }")"
rg -F -- "$EXPECTED" "$BUILD/CMakeCache.txt" >/dev/null || {
  print -u2 "Candidate build does not contain expected guard definition: $EXPECTED"
  exit 65
}

cmake --build "$BUILD" --target VibeAutotuneSignalChainDiagnostic --parallel 1
[[ -x "$DIAGNOSTIC" ]] || { print -u2 "Diagnostic build missing: $DIAGNOSTIC"; exit 67; }

mkdir -p "$OUT/hard_tune_natural_0"
"$DIAGNOSTIC" "$RAW" "$OUT/hard_tune_natural_0" 0 1 0 0 0 0 1 0 0 0 0 - 1 \
  > "$OUT/runner.log"

CSV="$OUT/hard_tune_natural_0/full_default_intervals.csv"
[[ -s "$CSV" ]] || { print -u2 "Diagnostic did not create its interval trace."; exit 68; }

# The problem passage is an A->B->A->B sequence.  Keep every commit and every
# selector guard decision around it, including preview/legato flags, so we can
# distinguish a guard that never engaged from one that engaged but was bypassed.
awk -F, '
  NR == 1 {
    for (i = 1; i <= NF; ++i) c[$i] = i
    print "time_ms,target_changed,target_before,previous_target,candidate,committed_target,frames_since_commit,selector_decision,preview_direction,rapid_legato_hard_lock,rapid_legato_target_changed"
    next
  }
  {
    t = $(c["timeMs"])
    decision = $(c["selectorDecision"])
    changed = $(c["targetChanged"])
    if (t >= 3550 && t <= 3820 && (changed == 1 || decision == 1 || decision == 2 || decision == 3))
      print t, changed, $(c["selectorCurrentTargetBefore"]), $(c["selectorPreviousTarget"]), \
        $(c["selectorCandidate"]), $(c["committedTargetMidi"]), $(c["selectorFramesSinceCommit"]), \
        decision, $(c["trajectoryPreviewDirection"]), $(c["rapidLegatoHardLock"]), \
        $(c["rapidLegatoTargetChanged"])
  }
' OFS=, "$CSV" > "$OUT/reversal-window-selector.csv"

awk -F, '
  NR == 1 { next }
  {
    count[$8]++
    if ($8 == 2) {
      guarded++
      if ($10 == 1) previewGuarded++
    }
  }
  END {
    print "# 64 ms reversal-guard selector verification"
    print ""
    print "- Guard decisions (code 2) in 3.550--3.820 s: " (guarded + 0)
    print "- Decision counts in the retained window: unchanged=" (count[0] + 0) ", direction=" (count[1] + 0) ", guard=" (count[2] + 0) ", commit=" (count[3] + 0)
    print "- Guard decisions while rapid_legato_hard_lock=1: " (previewGuarded + 0)
    print "- If this count is non-zero, the rapid-legato preview did not bypass the ordinary A->B->A guard in this candidate; any remaining mismatch is downstream in target timing/trajectory/rendering."
  }
' "$OUT/reversal-window-selector.csv" > "$OUT/selector-verification.md"

print ""
print "TRACE COMPLETE (not installed): $OUT"
print "Read first: $OUT/selector-verification.md"
print "Rows:       $OUT/reversal-window-selector.csv"
