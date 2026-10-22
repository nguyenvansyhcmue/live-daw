#!/bin/zsh
# Coordinate sweep of the existing Flex residual calibration control.
# Every run uses StudioForge's real VST3 host path; no candidate is installed.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
RUNNER="${STUDIOFORGE_CALIBRATION_RUNNER:-$DAW_ROOT/build-calibration-arm64/StudioForgeCalibrationRunner}"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST="/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
# This is a self-built VST3 and is never copied into the system plug-in folder.
VST3="${VIBE_FLEX_SWEEP_VST3:-$VIBE_ROOT/build-fast-musical-rail-240/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3}"
SCALES=(${=VIBE_FLEX_SWEEP_SCALES:-0.75 1.00 1.25})
# The Flex choice is ranked from correction transfer. Transition-window fitting
# reprocesses every one of the 24 bounces with expensive long convolutions and
# adds no decision value for this coordinate sweep. Opt in only when needed.
RUN_TRANSITION_FIT="${VIBE_FLEX_SWEEP_TRANSITIONS:-0}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-flex-residual-sweep-$STAMP"

[[ -f "$RAW" && -x "$RUNNER" && -f "$ANALYSER" && -f "$ARTIST" && -d "$VST3" ]] || {
  print -u2 "Missing Hook-2 WAV, runner, analyser, Artist reference, or candidate VST3."
  exit 66
}
mkdir -p "$OUT"

for scale in $SCALES; do
  [[ "$scale" == <-> || "$scale" == <->.<-> ]] || { print -u2 "Invalid scale: $scale"; exit 64; }
  case_dir="$OUT/flex_residual_$scale"
  mkdir -p "$case_dir/vibe"
  print "\n=== Flex residual scale $scale ==="
  VIBE_DIAG_FLEX_RESIDUAL="$scale" "$RUNNER" "$RAW" "$case_dir/vibe" VibeAutotune "$VST3" \
    | tee "$case_dir/vibe-runner.log"
  cp "$ARTIST" "$case_dir/artist-reference-calibration-report.csv"
  python3 "$ANALYSER" "$RAW" "$case_dir/vibe/calibration-report.csv" \
    "$case_dir/artist-reference-calibration-report.csv" "$case_dir/comparison"
  if [[ "$RUN_TRANSITION_FIT" == "1" ]]; then
    PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
      python3 /Users/hiimdrdey/autotune/fit_studioforge_transitions.py "$RAW" \
        "$case_dir/vibe/calibration-report.csv" "$case_dir/artist-reference-calibration-report.csv" \
        "$case_dir/transitions" --pitch-tools "$VIBE_ROOT/tools"
  fi
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
    python3 /Users/hiimdrdey/autotune/analyze_hook2_correction_transfer.py "$RAW" \
      "$case_dir/artist-reference-calibration-report.csv" "$case_dir/vibe/calibration-report.csv" \
      "$case_dir/transfer" --pitch-tools "$VIBE_ROOT/tools"
done

{
  print "# Hook-2 Flex residual sweep"
  print ""
  print "| diagnostic residual scale | Flex 25 | Flex 50 | Flex 75 | Flex 100 |"
  print "|---:|---|---|---|---|"
  for scale in $SCALES; do
    report="$OUT/flex_residual_$scale/transfer/transfer-report.md"
    f25=$(rg '^\| 5 \|' "$report" | sed 's/|/ /g' | awk '{print "slope=" $3 ", p90=" $5}')
    f50=$(rg '^\| 6 \|' "$report" | sed 's/|/ /g' | awk '{print "slope=" $3 ", p90=" $5}')
    f75=$(rg '^\| 7 \|' "$report" | sed 's/|/ /g' | awk '{print "slope=" $3 ", p90=" $5}')
    f100=$(rg '^\| 8 \|' "$report" | sed 's/|/ /g' | awk '{print "slope=" $3 ", p90=" $5}')
    print "| $scale | $f25 | $f50 | $f75 | $f100 |"
  done
} > "$OUT/flex-sweep-summary.md"

print ""
print "SWEEP COMPLETE (not installed): $OUT"
print "Read first: $OUT/flex-sweep-summary.md"
