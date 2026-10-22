#!/bin/zsh
# Offline-only test of the legal-scale-degree predictor gate: in F# minor,
# A57 -> B59 is one scale step although it spans two chromatic semitones.
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
OUT="$ROOT/artifacts/hook2-scale-degree-evidence-sweep-$(date +%Y%m%d-%H%M%S)"
typeset -a frames; frames=(8 6 5)
for file in "$RAW" "$ARTIST_REPORT" "$ARTIST_WAV" "$ANALYSER" "$JUCE/CMakeLists.txt" "$LINEAR/CMakeLists.txt" "$STRETCH/CMakeLists.txt"; do
  [[ -f "$file" ]] || { print -u2 "Missing required file: $file"; exit 2; }
done
mkdir -p "$OUT"; index=0
for frame_count in $frames; do
  (( ++index ))
  build="$VIBE_ROOT/build-hook2-scale-degree-evidence-${frame_count}"
  case_out="$OUT/evidence_${frame_count}frames"; mkdir -p "$case_out"
  print "[$index/${#frames}] testing legal-degree evidence window ${frame_count} frames"
  cmake -S "$VIBE_ROOT" -B "$build" -DCMAKE_BUILD_TYPE=Release \
    -DVIBE_JUCE_SOURCE_DIR:PATH="$JUCE" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$LINEAR" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$STRETCH" \
    -DCMAKE_CXX_FLAGS:STRING="-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_RAPID_ADJACENT_EVIDENCE_WINDOW_FRAMES=$frame_count" >/dev/null
  cmake --build "$build" --target VibeAutotuneSignalChainDiagnostic --parallel 1
  exe="$build/VibeAutotuneSignalChainDiagnostic"; [[ -x "$exe" ]] || { print -u2 "Diagnostic executable missing"; exit 3; }
  VIBE_RAPID_ADJACENT_SELECTOR=1 "$exe" "$RAW" "$case_out" 0 1 0 0 0 0 0 0 0 0 0 - 1 > "$case_out/runner.log"
  printf 'case,retune_ms,flex_tune,humanize,natural_vibrato,output\n0,0,0,0,0,"%s"\n' "$case_out/full_default_render.wav" > "$case_out/calibration-report.csv"
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ANALYSER" "$RAW" "$case_out/calibration-report.csv" "$ARTIST_REPORT" "$case_out/comparison"
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ROOT/analyze_artist_trajectory_delta.py" "$RAW" "$ARTIST_WAV" "$case_out/full_default_intervals.csv" "$case_out/trajectory" --pitch-tools "$VIBE_ROOT/tools" >/dev/null
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ROOT/fit_studioforge_transitions.py" "$RAW" "$case_out/calibration-report.csv" "$ARTIST_REPORT" "$case_out/transitions" --pitch-tools "$VIBE_ROOT/tools"
  python3 "$ROOT/analyze_hook2_transition_outliers.py" "$case_out/transitions/transition-events.csv" >/dev/null
  print "[$index/${#frames}] complete: $case_out"
done
summary="$OUT/summary.csv"
print 'evidence_frames,f0_median_delta_cents,artist_transitions,vibe_transitions,trajectory_median_abs_cents,trajectory_p90_abs_cents,at_3679_artist_target,at_3679_vibe_target,at_3679_delta_cents,worst_transition_score' > "$summary"
for frame_count in $frames; do
  case_out="$OUT/evidence_${frame_count}frames"
  base="$(awk -F, 'NR==2 {print $8 "," $9 "," $10}' "$case_out/comparison/calibration-report.csv")"
  traj="$(python3 - "$case_out/trajectory/artist-vibe-trajectory.csv" <<'PY'
import csv, numpy as np, sys
rows = list(csv.DictReader(open(sys.argv[1])))
delta = np.asarray([abs(float(row['vibe_minus_artist_correction_cents'])) for row in rows])
point = min(rows, key=lambda row: abs(float(row['time_seconds']) - 3.679))
print('{:.6f},{:.6f},{},{},{}'.format(
    np.median(delta), np.quantile(delta, .90),
    point['artist_inferred_target_midi'], point['vibe_target_midi'],
    point['vibe_minus_artist_correction_cents']))
PY
)"
  worst="$(awk -F'|' '/\| 0\/0\/0\/0 \|/ {gsub(/ /,"",$0); print $5; exit}' "$case_out/transitions/transition-outlier-report.md")"
  print "$frame_count,$base,$traj,$worst" >> "$summary"
done
printf '\nSWEEP COMPLETE (diagnostic only; not installed): %s\n' "$OUT"
printf 'Read first: %s\n' "$summary"
printf 'Promotion: <=29 transitions; improve 3.679 legal-degree mismatch; do not worsen trajectory median/P90 or worst transition.\n'
