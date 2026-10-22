#!/bin/zsh
# Measure a bounded hard-tune renderer-crossing contour. It affects only a
# coherent, fast adjacent-note preview; it does not alter knobs, Key/Scale,
# detector resolution, or global latency. Diagnostic only, never installed.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
RUNNER="${STUDIOFORGE_CALIBRATION_RUNNER:-$DAW_ROOT/build-calibration-arm64/StudioForgeCalibrationRunner}"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST="$ROOT/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
JUCE="$DAW_ROOT/build-macos-arm64/_deps/juce-src"
LINEAR="$VIBE_ROOT/.third_party/signalsmith_linear-src"
STRETCH="$VIBE_ROOT/.third_party/signalsmith_stretch-src"
WINDOWS="${VIBE_HARD_TUNE_CROSSING_WINDOWS_MS:-0 8 16 24}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$ROOT/artifacts/hook2-tdpsola-renderer-crossing-preview-sweep-$STAMP"

for item in "$RAW" "$RUNNER" "$ANALYSER" "$ARTIST" "$JUCE/CMakeLists.txt" "$LINEAR/CMakeLists.txt" "$STRETCH/CMakeLists.txt"; do
  [[ -e "$item" ]] || { print -u2 "Missing required input: $item"; exit 66; }
done
common_flags='-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_RAPID_ADJACENT_EVIDENCE_WINDOW_FRAMES=8 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=1024 -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=128'
mkdir -p "$OUT"
print 'crossing_ms,slope,median_abs_error,p90_abs_error,vibe_transitions,f0_median_delta,latency_samples' > "$OUT/summary.csv"

for window in ${(z)WINDOWS}; do
  [[ "$window" =~ '^[0-9]+$' && "$window" -le 32 ]] || { print -u2 "Crossing window must be an integer from 0 to 32 ms: $window"; exit 64; }
  build="$VIBE_ROOT/build-hook2-tdpsola-crossing-$window"
  case_dir="$OUT/crossing_${window}ms"
  flags="$common_flags -DVIBE_HARD_LOCK_RENDERER_CROSSING_TRANSITION_MS=$window.0"
  cmake -S "$VIBE_ROOT" -B "$build" -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release \
    -DVIBE_JUCE_SOURCE_DIR:PATH="$JUCE" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$LINEAR" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$STRETCH" \
    -DCMAKE_CXX_FLAGS:STRING="$flags"
  cmake --build "$build" --target VibeAutotune_VST3 --parallel 4
  candidate="$build/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
  mkdir -p "$case_dir/vibe"
  "$RUNNER" "$RAW" "$case_dir/vibe" VibeAutotune "$candidate" | tee "$case_dir/host-runner.log"
  awk -F, 'NR == 1 || $1 == 0' "$case_dir/vibe/calibration-report.csv" > "$case_dir/vibe-hardtune-report.csv"
  awk -F, 'NR == 1 || $1 == 0' "$ARTIST" > "$case_dir/artist-hardtune-report.csv"
  python3 "$ANALYSER" "$RAW" "$case_dir/vibe-hardtune-report.csv" "$case_dir/artist-hardtune-report.csv" "$case_dir/comparison"
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ROOT/fit_studioforge_transitions.py" "$RAW" "$case_dir/vibe-hardtune-report.csv" "$case_dir/artist-hardtune-report.csv" "$case_dir/transitions" --pitch-tools "$VIBE_ROOT/tools"
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$ROOT/analyze_hook2_correction_transfer.py" "$RAW" "$case_dir/artist-hardtune-report.csv" "$case_dir/vibe-hardtune-report.csv" "$case_dir/transfer" --pitch-tools "$VIBE_ROOT/tools" --write-frame-debug
  python3 "$ROOT/diagnose_hook2_transition_transfer.py" "$case_dir/transfer/transfer-frame-debug.csv" "$case_dir/transitions/transition-events.csv" "$case_dir/transition-transfer-diagnosis.md"
  python3 - "$window" "$case_dir" "$OUT/summary.csv" <<'PY'
import re, sys
window, case_dir, output = sys.argv[1:]
transfer = open(case_dir + '/transfer/transfer-report.md').read()
compare = open(case_dir + '/comparison/calibration-report.md').read()
def grab(pattern, text):
    match = re.search(pattern, text)
    if not match: raise SystemExit('Could not parse report')
    return match.group(1)
slope = grab(r'slope: ([0-9.]+)', transfer)
median = grab(r'Global median absolute movement error: ([0-9.]+)', transfer)
p90 = grab(r'\| 0 \| 0/0/0/0 \| [0-9.]+ \| [0-9.]+ \| ([0-9.]+) \|', transfer)
summary = re.search(r'\| 0 \| 2689 samples \| ([0-9]+) samples \| ([0-9.]+) cents \| 29 \| ([0-9]+) \|', compare)
if not summary: raise SystemExit('Could not parse comparison summary')
with open(output, 'a') as file:
    file.write(f'{window},{slope},{median},{p90},{summary.group(3)},{summary.group(2)},{summary.group(1)}\n')
PY
done

print ''
print "SWEEP COMPLETE (diagnostic only; not installed): $OUT"
print "Read first: $OUT/summary.csv"
print 'Promotion rule: transition-window median must improve below 13.59 cents; no more than 29 transitions; global median/P90 must not worsen.'
