#!/bin/zsh
# Final bounded sweep. The 28/50 fine candidate won F0 error, so only the
# 25-ms knot is moved toward the observed faster Artist response.
set -euo pipefail

if (( $# != 1 )); then
  print -u2 "usage: $0 /absolute/path/to/raw.wav"
  exit 64
fi

raw=${1:A}
root=/Users/hiimdrdey/code/daw
runner="$root/build-calibration-arm64/StudioForgeCalibrationRunner"
out="$root/retune-knot-final-fit"
fit=/Users/hiimdrdey/autotune/fit_studioforge_transitions.py

[[ -f $raw ]] || { print -u2 "missing input: $raw"; exit 66; }
[[ -x $runner ]] || { print -u2 "missing runner: $runner"; exit 1; }
[[ -f $fit ]] || { print -u2 "missing fitter: $fit"; exit 1; }

# All candidates retain a nearby 10-ms knot and probe only the remaining
# slower 25-ms response. 42 ms is above the diagnostic safety floor of 40.
for candidate in '26 42' '28 46' '30 50'; do
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
