#!/bin/zsh
# Research-only narrow delivery sweep for the pinned TD-PSOLA candidate.
# It never installs or replaces a plug-in.
set -euo pipefail

root=/Users/hiimdrdey/autotune
source_root="$root/artifacts/crossing24-bounded-preview-20261017-113341/source"
daw_root=/Users/hiimdrdey/code/daw
raw='/Users/hiimdrdey/Downloads/hook 2raw.wav'
artist="$root/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
runner="$daw_root/build-macos-arm64/StudioForgeCalibrationRunner"
analyser="$daw_root/Tools/analyze_studioforge_calibration.py"
tools="$source_root/tools"
out="${VIBE_NARROW_SWEEP_OUTPUT:-$root/artifacts/hook2-renderer-delivery-narrow-$(date +%Y%m%d-%H%M%S)}"
gains="${VIBE_TDPSOLA_DELIVERY_GAINS:-1.14 1.18 1.20}"

for item in "$source_root/CMakeLists.txt" "$raw" "$artist" "$runner" "$analyser" "$tools/compare_pitch_correction_bounces.py"; do
  [[ -e "$item" ]] || { print -u2 "Missing required input: $item"; exit 66; }
done
mkdir -p "$out"
print 'gain,hard_tune_slope,hard_tune_median_error,hard_tune_p90_error,artist_transitions,vibe_transitions,f0_median_delta' > "$out/summary.csv"

base_flags='-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_RAPID_ADJACENT_EVIDENCE_WINDOW_FRAMES=8 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=1024 -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=128 -DVIBE_TENOR_ANALYSIS_HOP_SAMPLES=128 -DVIBE_HARD_LOCK_RENDERER_CROSSING_TRANSITION_MS=24.0'
for gain in ${(z)gains}; do
  [[ "$gain" =~ '^1\.[0-9][0-9]?$' ]] || { print -u2 "Invalid gain: $gain"; exit 64; }
  tag=${gain//./_}; build="$source_root/build-delivery-$tag-research"; case_dir="$out/gain_$tag"
  cmake -S "$source_root" -B "$build" -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release \
    -DVIBE_JUCE_SOURCE_DIR:PATH="$daw_root/build-macos-arm64/_deps/juce-src" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$source_root/.third_party/signalsmith_linear-src" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$source_root/.third_party/signalsmith_stretch-src" \
    -DCMAKE_CXX_FLAGS:STRING="$base_flags -DVIBE_TDPSOLA_DELIVERY_GAIN=$gain"
  cmake --build "$build" --target VibeAutotune_VST3 --parallel 4
  candidate="$build/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
  mkdir -p "$case_dir/vibe"
  env STUDIOFORGE_CALIBRATION_VOICE=Alto STUDIOFORGE_CALIBRATION_KEY=F# STUDIOFORGE_CALIBRATION_SCALE='Natural Minor' \
    "$runner" "$raw" "$case_dir/vibe" VibeAutotune "$candidate" > "$case_dir/runner.log"
  awk -F, 'NR==1 || $1==0' "$case_dir/vibe/calibration-report.csv" > "$case_dir/vibe-hard.csv"
  awk -F, 'NR==1 || $1==0' "$artist" > "$case_dir/artist-hard.csv"
  PYTHONPATH="$tools${PYTHONPATH:+:$PYTHONPATH}" PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
    python3 "$analyser" "$raw" "$case_dir/vibe-hard.csv" "$case_dir/artist-hard.csv" "$case_dir/comparison"
  PYTHONPATH="$tools${PYTHONPATH:+:$PYTHONPATH}" PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
    python3 "$root/analyze_hook2_correction_transfer.py" "$raw" "$case_dir/artist-hard.csv" "$case_dir/vibe-hard.csv" "$case_dir/transfer" --pitch-tools "$tools"
  python3 - "$gain" "$case_dir" "$out/summary.csv" <<'PY'
import re, sys
gain, d, out = sys.argv[1:]
t=open(d+'/transfer/transfer-report.md').read(); c=open(d+'/comparison/calibration-report.md').read()
def one(p, s):
 m=re.search(p,s)
 if not m: raise SystemExit('metric absent: '+p)
 return m.group(1)
slope=one(r'\| 0 \| 0/0/0/0 \| ([0-9.]+)',t)
median=one(r'\| 0 \| 0/0/0/0 \| [0-9.]+ \| ([0-9.]+)',t)
p90=one(r'\| 0 \| 0/0/0/0 \| [0-9.]+ \| [0-9.]+ \| ([0-9.]+)',t)
m=re.search(r'\| 0 \| [0-9]+ samples \| [0-9]+ samples \| ([0-9.]+) cents \| ([0-9]+) \| ([0-9]+) \|',c)
if not m: raise SystemExit('case 0 comparison absent')
with open(out,'a') as f: f.write(','.join([gain,slope,median,p90,m.group(2),m.group(3),m.group(1)])+'\n')
PY
done
print "SWEEP COMPLETE (research only; not installed): $out"
print "Read first: $out/summary.csv"
