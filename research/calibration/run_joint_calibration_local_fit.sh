#!/bin/zsh
# Local coordinate fit around DOE winner 26/42/0.84/0.88/0.72.
set -euo pipefail
if (( $# != 1 )); then print -u2 "usage: $0 /absolute/path/to/raw.wav"; exit 64; fi
raw=${1:A}; root=/Users/hiimdrdey/code/daw
runner="$root/build-calibration-arm64/StudioForgeCalibrationRunner"
artist="$root/joint-calibration-doe/artist-cache/calibration-report.csv"
out="$root/joint-calibration-local-fit"
analyzer="$root/Tools/analyze_studioforge_calibration.py"
fit=/Users/hiimdrdey/autotune/fit_studioforge_transitions.py
[[ -f $raw && -x $runner && -f $artist ]] || { print -u2 'missing raw, runner, or Artist cache'; exit 1; }
mkdir -p "$out"
print 'candidate,t10_t90,t25_t90,flex_residual,humanize_scale,natural_phase' > "$out/candidates.csv"
for row in \
 'center 26 42 .84 .88 .72' 't10low 24 42 .84 .88 .72' 't10high 28 42 .84 .88 .72' \
 't25low 26 40 .84 .88 .72' 't25high 26 44 .84 .88 .72' \
 'flexlow 26 42 .78 .88 .72' 'flexhigh 26 42 .90 .88 .72' \
 'humanlow 26 42 .84 .80 .72' 'humanhigh 26 42 .84 .96 .72' \
 'phaselow 26 42 .84 .88 .60' 'phasehigh 26 42 .84 .88 .84'; do
  read -r id t10 t25 flex human phase <<< "$row"; dir="$out/$id"; mkdir -p "$dir/vibe"
  print "$id,$t10,$t25,$flex,$human,$phase" >> "$out/candidates.csv"; print "== $id =="
  VIBE_DIAG_RETUNE10_T90_MS="$t10" VIBE_DIAG_RETUNE25_T90_MS="$t25" \
  VIBE_DIAG_FLEX_RESIDUAL="$flex" VIBE_DIAG_HUMANIZE_SCALE="$human" VIBE_DIAG_NATURAL_PHASE="$phase" \
    "$runner" "$raw" "$dir/vibe" VibeAutotune >/dev/null
  python3 "$analyzer" "$raw" "$dir/vibe/calibration-report.csv" "$artist" "$dir/comparison" >/dev/null
  PYTHONPYCACHEPREFIX=/tmp/python-cache python3 "$fit" "$raw" "$dir/vibe/calibration-report.csv" "$artist" "$dir/transitions" --pitch-tools "$root/autotune/tools" >/dev/null
done
print "Complete: $out"
