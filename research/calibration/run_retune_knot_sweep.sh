#!/bin/zsh
# Diagnostic-only 3-point Retune-knot fit. Requires a Vibe component built
# with vibe-retune-knot-diagnostic.patch and the existing StudioForge runner.
set -euo pipefail

if (( $# != 1 )); then
  print -u2 "usage: $0 /absolute/path/to/raw.wav"
  exit 64
fi

raw=${1:A}
root=/Users/hiimdrdey/code/daw
runner="$root/build-calibration-arm64/StudioForgeCalibrationRunner"
out="$root/retune-knot-fit"
fit=/Users/hiimdrdey/autotune/fit_studioforge_transitions.py

[[ -f $raw ]] || { print -u2 "missing input: $raw"; exit 66; }
[[ -x $runner ]] || { print -u2 "missing runner: $runner"; exit 1; }
[[ -f $fit ]] || { print -u2 "missing fitter: $fit"; exit 1; }

# Current production is 53.333 / 96.0.  These three candidates surround the
# transition-fitter estimate (roughly 37 / 68 ms) without touching Retune 0,
# 50 ms, scheduler, renderer, OLA or latency.
for candidate in '34 64' '38 68' '42 72'; do
  read -r t90_10 t90_25 <<< "$candidate"
  tag="t10-${t90_10}_t25-${t90_25}"
  dir="$out/$tag"
  mkdir -p "$dir"
  print "== $tag =="
  VIBE_DIAG_RETUNE10_T90_MS="$t90_10" \
  VIBE_DIAG_RETUNE25_T90_MS="$t90_25" \
  STUDIOFORGE_CALIBRATION_RUNNER="$runner" \
    zsh "$root/Tools/run_studioforge_artist_vibe_calibration.sh" "$raw" "$dir"
  PYTHONPYCACHEPREFIX=/tmp/python-cache \
    python3 "$fit" "$raw" "$dir/vibe/calibration-report.csv" \
      "$dir/artist/calibration-report.csv" "$dir/transitions" \
      --pitch-tools "$root/autotune/tools"
done

print "Complete: $out"
