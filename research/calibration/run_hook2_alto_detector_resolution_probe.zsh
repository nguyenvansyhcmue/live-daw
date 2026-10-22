#!/bin/zsh
# One controlled detector A/B: default Alto 2048/256 vs 1024/128.
# It changes neither tuning controls nor renderer.  Nothing is installed.
set -euo pipefail
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
ROOT="/Users/hiimdrdey/autotune"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
ARTIST_REPORT="$ROOT/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
ARTIST_WAV="$ROOT/artifacts/hook2-artist-vibe-20261014-041857/artist/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
JUCE="$DAW_ROOT/build-macos-arm64/_deps/juce-src"
LINEAR="$VIBE_ROOT/.third_party/signalsmith_linear-src"
STRETCH="$VIBE_ROOT/.third_party/signalsmith_stretch-src"
OUT="$ROOT/artifacts/hook2-alto-detector-resolution-$(date +%Y%m%d-%H%M%S)"

for file in "$RAW" "$ARTIST_REPORT" "$ARTIST_WAV" "$ANALYSER" "$JUCE/CMakeLists.txt" "$LINEAR/CMakeLists.txt" "$STRETCH/CMakeLists.txt"; do
  [[ -f "$file" ]] || { print -u2 "Missing required file: $file"; exit 2; }
done

source_file="$VIBE_ROOT/VibeAutotune/PluginProcessor.cpp"
# Source files can have unrelated edits, so insert this small, default-neutral
# diagnostic seam by an exact semantic anchor rather than an old line-number
# patch.  It is idempotent and runs only in the user's source checkout.
python3 - "$source_file" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
marker = 'VIBE_ALTO_ANALYSIS_FRAME_SAMPLES'
needle = '        case 1: return { 2048, 256, 110.0, 700.0, 1 };'
replacement = '''        case 1: return { VIBE_ALTO_ANALYSIS_FRAME_SAMPLES, VIBE_ALTO_ANALYSIS_HOP_SAMPLES, 110.0, 700.0, 1 };'''
definitions = '''    // Diagnostic-only compile-time probe. Defaults preserve the released Alto contract.\n#ifndef VIBE_ALTO_ANALYSIS_FRAME_SAMPLES\n#define VIBE_ALTO_ANALYSIS_FRAME_SAMPLES 2048\n#endif\n#ifndef VIBE_ALTO_ANALYSIS_HOP_SAMPLES\n#define VIBE_ALTO_ANALYSIS_HOP_SAMPLES 256\n#endif\n'''
if marker not in s:
    if s.count(needle) != 1:
        raise SystemExit('Cannot find the unmodified Alto analysis configuration; no source was changed.')
    function_anchor = 'VibeAutotuneProcessor::PitchAnalysisConfig VibeAutotuneProcessor::getPitchAnalysisConfig (int inputType) const noexcept\n{\n'
    if s.count(function_anchor) != 1:
        raise SystemExit('Cannot find the Alto analysis function; no source was changed.')
    s = s.replace(function_anchor, function_anchor + definitions, 1).replace(needle, replacement, 1)
    p.write_text(s)
PY
rg -q 'VIBE_ALTO_ANALYSIS_FRAME_SAMPLES' "$VIBE_ROOT/VibeAutotune/PluginProcessor.cpp" \
  || { print -u2 'Could not install the diagnostic-only Alto probe marker'; exit 3; }

mkdir -p "$OUT"
typeset -a names frames hops
names=(baseline_2048_256 candidate_1024_128)
frames=(2048 1024)
hops=(256 128)

for i in {1..2}; do
  name="${names[$i]}"; frame="${frames[$i]}"; hop="${hops[$i]}"
  build="$VIBE_ROOT/build-hook2-alto-detector-${frame}-${hop}"
  case_out="$OUT/$name"; mkdir -p "$case_out"
  print "[$i/2] $name (Alto frame=$frame, hop=$hop)"
  cmake -S "$VIBE_ROOT" -B "$build" -DCMAKE_BUILD_TYPE=Release \
    -DVIBE_JUCE_SOURCE_DIR:PATH="$JUCE" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$LINEAR" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$STRETCH" \
    -DCMAKE_CXX_FLAGS:STRING="-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_RAPID_ADJACENT_EVIDENCE_WINDOW_FRAMES=8 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=$frame -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=$hop" >/dev/null
  cmake --build "$build" --target VibeAutotuneSignalChainDiagnostic --parallel 1
  exe="$build/VibeAutotuneSignalChainDiagnostic"; [[ -x "$exe" ]] || { print -u2 'Diagnostic executable missing'; exit 4; }
  VIBE_RAPID_ADJACENT_SELECTOR=1 "$exe" "$RAW" "$case_out" 0 1 0 0 0 0 0 0 0 0 0 - 1 > "$case_out/runner.log"
  printf 'case,retune_ms,flex_tune,humanize,natural_vibrato,output\n0,0,0,0,0,"%s"\n' "$case_out/full_default_render.wav" > "$case_out/calibration-report.csv"
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ANALYSER" "$RAW" "$case_out/calibration-report.csv" "$ARTIST_REPORT" "$case_out/comparison" >/dev/null
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ROOT/analyze_artist_trajectory_delta.py" "$RAW" "$ARTIST_WAV" "$case_out/full_default_intervals.csv" "$case_out/trajectory" --pitch-tools "$VIBE_ROOT/tools" >/dev/null
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ROOT/audit_vibe_detector_midpoint.py" "$RAW" "$case_out/full_default_intervals.csv" "$case_out/detector" --pitch-tools "$VIBE_ROOT/tools" --vibe-frame-samples "$frame" >/dev/null
done

summary="$OUT/summary.csv"
print 'case,alto_frame,alto_hop,publication_lag_ms,detector_centre_lag_ms,detector_median_abs_cents,detector_p90_abs_cents,artist_transitions,vibe_transitions,trajectory_median_abs_cents,trajectory_p90_abs_cents,at_3679_artist_target,at_3679_vibe_target,at_3679_delta_cents' > "$summary"
for i in {1..2}; do
  name="${names[$i]}"; frame="${frames[$i]}"; hop="${hops[$i]}"; case_out="$OUT/$name"
  detector="$(python3 - "$case_out/detector/detector-midpoint-report.md" <<'PY'
import re, sys
s=open(sys.argv[1]).read()
def n(label):
 m=re.search(label+r': ([0-9.]+)',s); return m.group(1) if m else 'nan'
print(','.join([n('Vibe publication minus reference centre'),n('Vibe detector centre minus reference centre'),n('Detector median absolute disagreement'),n('Detector P90 absolute disagreement')]))
PY
)"
  compare="$(awk -F, 'NR==2 {print $9 "," $10}' "$case_out/comparison/calibration-report.csv")"
  traj="$(python3 - "$case_out/trajectory/artist-vibe-trajectory.csv" <<'PY'
import csv,numpy as np,sys
r=list(csv.DictReader(open(sys.argv[1])))
d=np.asarray([abs(float(x['vibe_minus_artist_correction_cents'])) for x in r])
p=min(r,key=lambda x:abs(float(x['time_seconds'])-3.679))
print('{:.6f},{:.6f},{},{},{}'.format(np.median(d),np.quantile(d,.9),p['artist_inferred_target_midi'],p['vibe_target_midi'],p['vibe_minus_artist_correction_cents']))
PY
)"
  print "$name,$frame,$hop,$detector,$compare,$traj" >> "$summary"
done
cat "$summary"
printf '\nPROBE COMPLETE (diagnostic only; not installed): %s\n' "$OUT"
printf 'Read first: %s\n' "$summary"
printf 'Promote only if the candidate materially reduces midpoint lag AND does not worsen pitch trajectory or transition count.\n'
