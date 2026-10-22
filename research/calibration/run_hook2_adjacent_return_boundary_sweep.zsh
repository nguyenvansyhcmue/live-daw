#!/bin/zsh
# Offline-only selector sweep for the default Hook-2 hard-tune preset.
# It never builds/installs VST3 or AU; each result is compared to the fixed
# Artist reference before any candidate may be considered for promotion.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
ARTIST_REPORT="${HOOK2_ARTIST_REPORT:-/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv}"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
JUCE_SOURCE="${VIBE_JUCE_SOURCE_DIR:-$DAW_ROOT/build-macos-arm64/_deps/juce-src}"
SIGNALSMITH_LINEAR_SOURCE="${VIBE_SIGNALSMITH_LINEAR_SOURCE:-$VIBE_ROOT/.third_party/signalsmith_linear-src}"
SIGNALSMITH_STRETCH_SOURCE="${VIBE_SIGNALSMITH_STRETCH_SOURCE:-$VIBE_ROOT/.third_party/signalsmith_stretch-src}"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-adjacent-return-boundary-sweep-$(date +%Y%m%d-%H%M%S)"

# Four-cent is the current baseline. The remaining values allow an adjacent
# return only 4/8/12 cents before the raw midpoint, still requiring all of
# the existing high-confidence, dwell, and multi-frame predictor evidence.
# Keep every current candidate compile flag across *every* arm. Without these,
# a sweep would compare against a different renderer/rail architecture.
typeset -a entries
entries=(4 0 -4 -8)

for required_file in "$RAW" "$ARTIST_REPORT" "$ANALYSER" \
                     "$JUCE_SOURCE/CMakeLists.txt" \
                     "$SIGNALSMITH_LINEAR_SOURCE/CMakeLists.txt" \
                     "$SIGNALSMITH_STRETCH_SOURCE/CMakeLists.txt"; do
  [[ -f "$required_file" ]] || { print -u2 "Missing required file: $required_file"; exit 2; }
done

mkdir -p "$OUT"
arm_index=0
for entry in $entries; do
  (( ++arm_index ))
  tag="${entry//-/neg}"
  build="$VIBE_ROOT/build-hook2-adjacent-entry-$tag"
  case_out="$OUT/entry_${tag}"
  mkdir -p "$case_out"

  print "[$arm_index/${#entries}] testing adjacent-entry threshold ${entry} cents"

  cmake -S "$VIBE_ROOT" -B "$build" \
    -DCMAKE_BUILD_TYPE=Release \
    -DVIBE_JUCE_SOURCE_DIR:PATH="$JUCE_SOURCE" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$SIGNALSMITH_LINEAR_SOURCE" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$SIGNALSMITH_STRETCH_SOURCE" \
    -DCMAKE_CXX_FLAGS:STRING="-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=$entry" >/dev/null
  cmake --build "$build" --target VibeAutotuneSignalChainDiagnostic --parallel 1

  diagnostic="$build/VibeAutotuneSignalChainDiagnostic"
  [[ -x "$diagnostic" ]] || { print -u2 "Diagnostic executable missing: $diagnostic"; exit 3; }

  # Default target: Alto/F# Natural Minor, Retune/Flex/Humanize/Natural = 0,
  # Formant on, Tracking 50, causal TD-PSOLA. Argument 9=0 selects TD-PSOLA.
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
  print "[$arm_index/${#entries}] complete: $case_out"
done

summary="$OUT/summary.csv"
print 'entry_cents,f0_median_delta_cents,artist_transitions,vibe_transitions,median_outlier_score,worst_outlier_score' > "$summary"
for entry in $entries; do
  tag="${entry//-/neg}"
  report="$OUT/entry_${tag}/comparison/calibration-report.csv"
  outliers="$OUT/entry_${tag}/transitions/transition-outlier-report.md"
  row="$(awk -F, 'NR == 2 { print $8 "," $9 "," $10 }' "$report")"
  scores="$(awk -F'|' '/\| 0\/0\/0\/0 \|/ { gsub(/ /, "", $0); print $4 "," $5; exit }' "$outliers")"
  print "$entry,$row,$scores" >> "$summary"
done

printf '\nSWEEP COMPLETE (diagnostic only; not installed): %s\n' "$OUT"
printf 'Read first: %s\n' "$summary"
printf '%s\n' 'Promotion rule: candidate must not raise transition count above Artist (29),' \
              'must improve the 4.631/4.447 window, and must not worsen median/p90 pitch error.'
