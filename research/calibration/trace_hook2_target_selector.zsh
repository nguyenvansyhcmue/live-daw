#!/bin/zsh
# Trace the exact Vibe target-selection path on Hook 2.  This is a
# diagnostic render only; it does not install or modify the production VST3.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
BUILD="${VIBE_BUILD:-$VIBE_ROOT/build-studioforge-juce8-stable}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
DIAGNOSTIC="$BUILD/VibeAutotuneSignalChainDiagnostic"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-target-selector-$STAMP"
BUILD_LOG="/Users/hiimdrdey/autotune/artifacts/hook2-target-selector-build-$STAMP.log"

[[ -f "$RAW" ]] || { print -u2 "Missing source WAV: $RAW"; exit 2; }

cd "$VIBE_ROOT"
compat_patch="/Users/hiimdrdey/autotune/signal_chain_diagnostic_juce7_writer_compat.patch"
if git apply --reverse --check "$compat_patch" >/dev/null 2>&1; then
  print "JUCE 7 diagnostic writer compatibility patch already applied."
else
  git apply "$compat_patch"
  print "Applied JUCE 7 diagnostic writer compatibility patch."
fi
if ! cmake --build "$BUILD" --target VibeAutotuneSignalChainDiagnostic --parallel 1 2>&1 | tee "$BUILD_LOG"; then
  print -u2 ""
  print -u2 "BUILD FAILED. Full compiler log: $BUILD_LOG"
  exit 1
fi
[[ -x "$DIAGNOSTIC" ]] || { print -u2 "Diagnostic executable was not built: $DIAGNOSTIC"; exit 2; }

mkdir -p "$OUT"

# Args bind the public Artist-comparison preset exactly:
# Classic off, Formant on, Retune 0, Flex 0, Humanize 0, F# Natural Minor,
# Alto, Tracking 50.  The environment enables the same adjacent-note policy
# currently selected by the production processor.
run_case() {
  local name="$1"
  local natural="$2"
  local destination="$OUT/$name"
  mkdir -p "$destination"
  VIBE_RAPID_ADJACENT_SELECTOR=1 "$DIAGNOSTIC" "$RAW" "$destination" \
    0 1 0 0 0 0 1 0 0 0 "$natural" - 1 > "$destination/runner.log"
}

run_case hard_tune_natural_0 0
run_case hard_tune_natural_plus12 12

# Selector decision codes: 0 unchanged; 1 direction guard; 2 reversal/lock
# guard; 3 committed; 4 midpoint guard; 5 persistence wait; 6 initial wait.
for case_dir in "$OUT"/*; do
  csv="$case_dir/full_default_intervals.csv"
  [[ -f "$csv" ]] || continue
  awk -F, '
    NR == 1 { for (i=1; i<=NF; ++i) col[$i]=i; next }
    {
      decision=$(col["selectorDecision"]);
      decisions[decision]++;
      if ($(col["targetChanged"]) == 1)
        printf "commit,time_ms=%.3f,target=%s,candidate=%s,raw_midi=%s,decision=%s,pending=%s,excess_ct=%.2f\n", \
          $(col["timeMs"]), $(col["committedTargetMidi"]), $(col["selectorCandidate"]), \
          $(col["rawMidi"]), decision, $(col["pendingTargetFrames"]), $(col["targetDecisionExcessCents"]);
    }
    END {
      printf "decision_counts";
      for (i=0; i<=6; ++i) printf ",%d=%d", i, decisions[i] + 0;
      print "";
    }
  ' "$csv" > "$case_dir/selector-summary.txt"
done

print ""
print "COMPLETE: $OUT"
print "Read:     $OUT/hard_tune_natural_0/selector-summary.txt"
print "Trace:    $OUT/hard_tune_natural_0/full_default_intervals.csv"
