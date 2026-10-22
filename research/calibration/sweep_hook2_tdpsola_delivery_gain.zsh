#!/bin/zsh
# Offline calibration sweep. Each point is host-rendered through StudioForge;
# nothing is installed or promoted by this script.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
RAW="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
RUNNER="${STUDIOFORGE_CALIBRATION_RUNNER:-$DAW_ROOT/build-calibration-arm64/StudioForgeCalibrationRunner}"
ANALYSER="$DAW_ROOT/Tools/analyze_studioforge_calibration.py"
ARTIST="/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
MODE_PATCH="/Users/hiimdrdey/autotune/vibe-tdpsola-host-ab-config.patch"
GAIN_PATCH="/Users/hiimdrdey/autotune/vibe-tdpsola-delivery-gain-config.patch"
GAINS="${VIBE_TDPSOLA_DELIVERY_GAINS:-1.10 1.20 1.30}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/hook2-tdpsola-delivery-gain-sweep-$STAMP"

[[ -f "$RAW" && -x "$RUNNER" && -f "$ANALYSER" && -f "$ARTIST" ]] || {
  print -u2 "Missing Hook-2 WAV, host runner, analyser, or Artist reference."
  exit 66
}
cd "$VIBE_ROOT"
for PATCH in "$MODE_PATCH" "$GAIN_PATCH"; do
  marker="VIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE"
  [[ "$PATCH" == "$GAIN_PATCH" ]] && marker="VIBE_TDPSOLA_DELIVERY_GAIN"
  if ! rg -q "$marker" VibeAutotune/PluginProcessor.cpp; then git apply "$PATCH"; fi
done
mkdir -p "$OUT"
print 'gain,slope,median_abs_error,p90_abs_error,vibe_transitions,f0_median_delta,latency_samples' > "$OUT/summary.csv"

for GAIN in ${(z)GAINS}; do
  [[ "$GAIN" =~ '^1\.[0-9][0-9]?$' ]] || { print -u2 "Invalid gain: $GAIN"; exit 64; }
  TAG="${GAIN//./_}"
  BUILD="$VIBE_ROOT/build-tdpsola-gain-$TAG"
  CASE="$OUT/gain_$TAG"
  cmake -S "$VIBE_ROOT" -B "$BUILD" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_FLAGS="-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_TDPSOLA_DELIVERY_GAIN=$GAIN" \
    -DVIBE_JUCE_SOURCE_DIR="$DAW_ROOT/build-macos-arm64/_deps/juce-src" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR="$VIBE_ROOT/.third_party/signalsmith_linear-src" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH="$VIBE_ROOT/.third_party/signalsmith_stretch-src"
  cmake --build "$BUILD" --target VibeAutotune_VST3 --parallel 8
  CANDIDATE="$BUILD/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
  mkdir -p "$CASE/vibe"
  "$RUNNER" "$RAW" "$CASE/vibe" VibeAutotune "$CANDIDATE" > "$CASE/host-runner.log"
  awk -F, 'NR == 1 || $1 == 0' "$CASE/vibe/calibration-report.csv" > "$CASE/vibe-hardtune-report.csv"
  awk -F, 'NR == 1 || $1 == 0' "$ARTIST" > "$CASE/artist-hardtune-report.csv"
  python3 "$ANALYSER" "$RAW" "$CASE/vibe-hardtune-report.csv" "$CASE/artist-hardtune-report.csv" "$CASE/comparison"
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 /Users/hiimdrdey/autotune/fit_studioforge_transitions.py \
    "$RAW" "$CASE/vibe-hardtune-report.csv" "$CASE/artist-hardtune-report.csv" "$CASE/transitions" --pitch-tools "$VIBE_ROOT/tools"
  PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 /Users/hiimdrdey/autotune/analyze_hook2_correction_transfer.py \
    "$RAW" "$CASE/artist-hardtune-report.csv" "$CASE/vibe-hardtune-report.csv" "$CASE/transfer" --pitch-tools "$VIBE_ROOT/tools"
  python3 /Users/hiimdrdey/autotune/analyze_hook2_transition_outliers.py "$CASE/transitions/transition-events.csv"
  python3 - "$GAIN" "$CASE" "$OUT/summary.csv" <<'PY'
import csv, re, sys
gain, case, output = sys.argv[1:]
transfer = open(case + '/transfer/transfer-report.md').read()
compare = open(case + '/comparison/calibration-report.md').read()
def grab(pattern, text):
    return re.search(pattern, text).group(1)
slope = grab(r'slope: ([0-9.]+)', transfer)
median = grab(r'Global median absolute movement error: ([0-9.]+)', transfer)
p90 = re.search(r'\| 0 \| 0/0/0/0 \| [0-9.]+ \| [0-9.]+ \| ([0-9.]+) \|', transfer).group(1)
row = next(csv.DictReader(compare.splitlines()[2:])) if False else None
numbers = re.search(r'\| 0 \| 2689 samples \| ([0-9]+) samples \| ([0-9.]+) cents \| 29 \| ([0-9]+) \|', compare)
with open(output, 'a') as f:
    f.write(f'{gain},{slope},{median},{p90},{numbers.group(3)},{numbers.group(2)},{numbers.group(1)}\n')
PY
done

print ""
print "SWEEP COMPLETE (not installed): $OUT"
print "Read first: $OUT/summary.csv"
