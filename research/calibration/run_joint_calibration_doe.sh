#!/bin/zsh
# Joint control-law calibration. Artist is rendered once and cached; every
# subsequent candidate renders Vibe only through StudioForge's normal host.
set -euo pipefail

if (( $# != 1 )); then
  print -u2 "usage: $0 /absolute/path/to/raw.wav"
  exit 64
fi

raw=${1:A}
root=/Users/hiimdrdey/code/daw
runner="$root/build-calibration-arm64/StudioForgeCalibrationRunner"
out="$root/joint-calibration-doe"
analyzer="$root/Tools/analyze_studioforge_calibration.py"
fit=/Users/hiimdrdey/autotune/fit_studioforge_transitions.py

[[ -f $raw ]] || { print -u2 "missing input: $raw"; exit 66; }
[[ -x $runner ]] || { print -u2 "missing runner: $runner"; exit 1; }

mkdir -p "$out/artist-cache"
if [[ ! -f "$out/artist-cache/calibration-report.csv" ]]; then
  print '== Artist cache =='
  "$runner" "$raw" "$out/artist-cache" 'Auto-Tune Artist' >/dev/null
fi

print 'candidate,t10_t90,t25_t90,flex_residual,humanize_scale,natural_phase' > "$out/candidates.csv"

# Deterministic 12-point fractional factorial: bounded around measured
# Retune winners while independently covering Flex/Humanize/Natural axes.
for row in \
  '01 26 42 0.84 0.88 0.72' \
  '02 26 46 0.90 1.04 0.96' \
  '03 26 50 0.98 1.16 1.20' \
  '04 28 42 1.06 1.12 0.84' \
  '05 28 46 0.92 0.96 1.08' \
  '06 28 50 1.00 1.08 0.76' \
  '07 30 42 0.88 1.20 1.12' \
  '08 30 46 1.04 0.92 0.88' \
  '09 30 50 0.96 1.00 1.16' \
  '10 28 46 1.00 1.00 1.00' \
  '11 28 46 0.90 1.10 0.90' \
  '12 28 46 1.10 0.90 1.10'; do
  read -r id t10 t25 flex humanize phase <<< "$row"
  tag="candidate-${id}"
  dir="$out/$tag"
  mkdir -p "$dir/vibe"
  print "$id,$t10,$t25,$flex,$humanize,$phase" >> "$out/candidates.csv"
  print "== $tag =="
  VIBE_DIAG_RETUNE10_T90_MS="$t10" \
  VIBE_DIAG_RETUNE25_T90_MS="$t25" \
  VIBE_DIAG_FLEX_RESIDUAL="$flex" \
  VIBE_DIAG_HUMANIZE_SCALE="$humanize" \
  VIBE_DIAG_NATURAL_PHASE="$phase" \
    "$runner" "$raw" "$dir/vibe" VibeAutotune >/dev/null
  python3 "$analyzer" "$raw" "$dir/vibe/calibration-report.csv" \
    "$out/artist-cache/calibration-report.csv" "$dir/comparison" >/dev/null
  PYTHONPYCACHEPREFIX=/tmp/python-cache \
    python3 "$fit" "$raw" "$dir/vibe/calibration-report.csv" \
      "$out/artist-cache/calibration-report.csv" "$dir/transitions" \
      --pitch-tools "$root/autotune/tools" >/dev/null
done

print "Complete: $out"
