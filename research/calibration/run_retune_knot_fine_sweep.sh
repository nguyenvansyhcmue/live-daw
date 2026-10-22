#!/bin/zsh
# Second-pass fit around the coarse winner (T90: Retune 10/25 = 34/64 ms).
# It modifies no production source: each candidate enters only through the
# verified hidden AU calibration parameters.
set -euo pipefail

if (( $# != 1 )); then
  print -u2 "usage: $0 /absolute/path/to/raw.wav"
  exit 64
fi

raw=${1:A}
root=/Users/hiimdrdey/code/daw
runner="$root/build-calibration-arm64/StudioForgeCalibrationRunner"
out="$root/retune-knot-fine-fit"
fit=/Users/hiimdrdey/autotune/fit_studioforge_transitions.py

[[ -f $raw ]] || { print -u2 "missing input: $raw"; exit 66; }
[[ -x $runner ]] || { print -u2 "missing runner: $runner"; exit 1; }
[[ -f $fit ]] || { print -u2 "missing fitter: $fit"; exit 1; }

# Coarse response says 34/64 wins. These bounded faster candidates resolve
# the remaining positive 25-ms lag without changing Retune 0/50 or any DSP
# topology. The centre candidate avoids extrapolating beyond measured data.
for candidate in '28 50' '30 54' '32 58'; do
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
