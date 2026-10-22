#!/bin/zsh
# Negative-Natural phase calibration on a voiced vibrato fixture.
set -euo pipefail
if (( $# != 1 )); then print -u2 "usage: $0 /absolute/path/to/vibrato-source.mp3-or-wav"; exit 64; fi
input=${1:A}; root=/Users/hiimdrdey/code/daw
runner="$root/build-calibration-arm64/StudioForgeCalibrationRunner"
out="$root/natural-vibrato-phase-fit-retune10"
analyzer="$root/Tools/analyze_studioforge_calibration.py"
fit=/Users/hiimdrdey/autotune/fit_studioforge_transitions.py
[[ -f $input && -x $runner ]] || { print -u2 'missing input or runner'; exit 1; }

# scipy's WAV reader powers the F0/transition tools, so normalize compressed
# fixtures once before *both* plug-ins are rendered. This keeps source timing
# and channel layout identical for Artist, Vibe and analysis.
fixture="$out/fixture-48k.wav"
fixtureManifest="$out/fixture-source.txt"
mkdir -p "$out"
if [[ ! -f $fixture || ! -f $fixtureManifest || "$(< "$fixtureManifest")" != "$input" ]]; then
  command -v ffmpeg >/dev/null || { print -u2 'ffmpeg is required to decode this fixture'; exit 1; }
  print '== Decode fixture to analysis WAV =='
  ffmpeg -v error -y -i "$input" -ar 48000 -ac 2 -c:a pcm_s24le "$fixture"
  print -r -- "$input" > "$fixtureManifest"
  # These are generated calibration artifacts for the previous source
  # representation; invalidate them rather than mixing incompatible traces.
  rm -rf "$out/artist-cache" "$out"/phase-*(N)
fi

input="$fixture"
mkdir -p "$out/artist-cache"
if [[ ! -f "$out/artist-cache/calibration-report.csv" ]]; then
  print '== Artist vibrato cache =='
  STUDIOFORGE_NATURAL_FIT_RETUNE_MS=10 \
    "$runner" "$input" "$out/artist-cache" 'Auto-Tune Artist' >/dev/null
fi
print 'phase_scale' > "$out/candidates.csv"
for phase in 0.25 0.50 0.75 1.00 1.25 1.50; do
  tag="phase-${phase}"; dir="$out/$tag"; mkdir -p "$dir/vibe"
  print "$phase" >> "$out/candidates.csv"; print "== $tag =="
  # Resume a completed render/analysis after an interrupted long fixture.
  [[ -f "$dir/comparison/calibration-report.csv" ]] && continue
  VIBE_DIAG_RETUNE10_T90_MS=24 VIBE_DIAG_RETUNE25_T90_MS=42 \
  VIBE_DIAG_FLEX_RESIDUAL=.74 VIBE_DIAG_HUMANIZE_SCALE=.80 \
  VIBE_DIAG_NATURAL_PHASE="$phase" \
  STUDIOFORGE_NATURAL_FIT_RETUNE_MS=10 \
    "$runner" "$input" "$dir/vibe" VibeAutotune >/dev/null
  python3 "$analyzer" "$input" "$dir/vibe/calibration-report.csv" "$out/artist-cache/calibration-report.csv" "$dir/comparison" >/dev/null
done
print "Complete: $out"
