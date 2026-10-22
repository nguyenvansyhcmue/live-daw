#!/bin/zsh
# Offline-only dwell-time sweep for the Hook-2 default hard-tune selector.
# It preserves the active TD-PSOLA / rail-160 / legal-neighbour candidate and
# never installs a plug-in bundle.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
ARTIST_REPORT="${HOOK2_ARTIST_REPORT:-/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv}"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
JUCE_SOURCE="${VIBE_JUCE_SOURCE_DIR:-$DAW_ROOT/build-macos-arm64/_deps/juce-src}"
SIGNALSMITH_LINEAR_SOURCE="${VIBE_SIGNALSMITH_LINEAR_SOURCE:-$VIBE_ROOT/.third_party/signalsmith_linear-src}"
SIGNALSMITH_STRETCH_SOURCE="${VIBE_SIGNALSMITH_STRETCH_SOURCE:-$VIBE_ROOT/.third_party/signalsmith_stretch-src}"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-adjacent-dwell-sweep-$(date +%Y%m%d-%H%M%S)"

# Samples at 48 kHz: 80 ms is current; lower arms admit a *fully existing*
# high-confidence adjacent predictor earlier, without changing its midpoint,
# scale policy, renderer, or any public control.
typeset -a dwell_samples
dwell_samples=(3840 3072 2304 1536)

for required_file in "$RAW" "$ARTIST_REPORT" "$ANALYSER" \
                     "$JUCE_SOURCE/CMakeLists.txt" \
                     "$SIGNALSMITH_LINEAR_SOURCE/CMakeLists.txt" \
                     "$SIGNALSMITH_STRETCH_SOURCE/CMakeLists.txt"; do
  [[ -f "$required_file" ]] || { print -u2 "Missing required file: $required_file"; exit 2; }
done

mkdir -p "$OUT"
arm_index=0
for dwell in $dwell_samples; do
  (( ++arm_index ))
  milliseconds=$(awk "BEGIN { printf \"%.0f\", $dwell * 1000.0 / 48000.0 }")
  build="$VIBE_ROOT/build-hook2-adjacent-dwell-${dwell}"
  case_out="$OUT/dwell_${milliseconds}ms"
  mkdir -p "$case_out"
  print "[$arm_index/${#dwell_samples}] testing raw-predictor dwell ${milliseconds} ms"

  cmake -S "$VIBE_ROOT" -B "$build" \
    -DCMAKE_BUILD_TYPE=Release \
    -DVIBE_JUCE_SOURCE_DIR:PATH="$JUCE_SOURCE" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$SIGNALSMITH_LINEAR_SOURCE" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$SIGNALSMITH_STRETCH_SOURCE" \
    -DCMAKE_CXX_FLAGS:STRING="-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=$dwell" >/dev/null
  cmake --build "$build" --target VibeAutotuneSignalChainDiagnostic --parallel 1

  diagnostic="$build/VibeAutotuneSignalChainDiagnostic"
  [[ -x "$diagnostic" ]] || { print -u2 "Diagnostic executable missing: $diagnostic"; exit 3; }
  VIBE_RAPID_ADJACENT_SELECTOR=1 "$diagnostic" "$RAW" "$case_out" \
    0 1 0 0 0 0 0 0 0 0 0 - 1 > "$case_out/runner.log"
  printf 'case,retune_ms,flex_tune,humanize,natural_vibrato,output\n0,0,0,0,0,"%s"\n' \
    "$case_out/full_default_render.wav" > "$case_out/calibration-report.csv"
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ANALYSER" \
    "$RAW" "$case_out/calibration-report.csv" "$ARTIST_REPORT" "$case_out/comparison"
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 \
    /Users/hiimdrdey/autotune/fit_studioforge_transitions.py \
    "$RAW" "$case_out/calibration-report.csv" "$ARTIST_REPORT" "$case_out/transitions" \
    --pitch-tools "$VIBE_ROOT/tools"
  python3 /Users/hiimdrdey/autotune/analyze_hook2_transition_outliers.py \
    "$case_out/transitions/transition-events.csv" >/dev/null
  print "[$arm_index/${#dwell_samples}] complete: $case_out"
done

summary="$OUT/summary.csv"
print 'dwell_ms,f0_median_delta_cents,artist_transitions,vibe_transitions,median_outlier_score,worst_outlier_score,event_4631_score,event_4447_score' > "$summary"
for dwell in $dwell_samples; do
  milliseconds=$(awk "BEGIN { printf \"%.0f\", $dwell * 1000.0 / 48000.0 }")
  report="$OUT/dwell_${milliseconds}ms/comparison/calibration-report.csv"
  outliers="$OUT/dwell_${milliseconds}ms/transitions/transition-outlier-report.md"
  row="$(awk -F, 'NR == 2 { print $8 "," $9 "," $10 }' "$report")"
  surface="$(awk -F'|' '/\| 0\/0\/0\/0 \|/ { gsub(/ /, "", $0); print $4 "," $5; exit }' "$outliers")"
  e4631="$(awk -F'|' '/\| 0\/0\/0\/0 \| 4\.631 \|/ { gsub(/ /, "", $0); print $8; exit }' "$outliers")"
  e4447="$(awk -F'|' '/\| 0\/0\/0\/0 \| 4\.447 \|/ { gsub(/ /, "", $0); print $8; exit }' "$outliers")"
  print "$milliseconds,$row,$surface,$e4631,$e4447" >> "$summary"
done

printf '\nSWEEP COMPLETE (diagnostic only; not installed): %s\n' "$OUT"
printf 'Read first: %s\n' "$summary"
