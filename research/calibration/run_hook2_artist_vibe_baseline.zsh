#!/bin/zsh
# Deterministic black-box comparison for the current VibeAutotune build versus
# Auto-Tune Artist. It does not modify either plug-in, its presets, or the
# running StudioForge application.
set -euo pipefail

ROOT="${STUDIOFORGE_ROOT:-/Users/hiimdrdey/code/daw}"
BUILD="${STUDIOFORGE_CALIBRATION_BUILD:-$ROOT/build-calibration-arm64}"
RAW="${1:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
SCRIPT_DIR="${0:A:h}"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT="${2:-$SCRIPT_DIR/artifacts/hook2-artist-vibe-$STAMP}"
VIBE_VST3="${VIBE_VST3_PATH:-/Users/hiimdrdey/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3}"
RUNNER="$BUILD/StudioForgeCalibrationRunner"
ANALYSER="$ROOT/Tools/analyze_studioforge_calibration.py"
FIT="$SCRIPT_DIR/fit_studioforge_transitions.py"

[[ -f "$RAW" ]] || { print -u2 "Missing raw vocal WAV: $RAW"; exit 66; }
[[ -d "$VIBE_VST3" ]] || { print -u2 "Missing Vibe VST3: $VIBE_VST3"; exit 66; }
[[ -f "$ROOT/CMakeLists.txt" ]] || { print -u2 "Missing StudioForge source: $ROOT"; exit 66; }

# The old runner binary pre-dates the protected VST3 probe. Reconfigure so the
# comparison uses the same generic host path as the application, then build
# only the offline runner and its scanner helper.
cmake -S "$ROOT" -B "$BUILD" -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build "$BUILD" --target StudioForgeVst3Probe StudioForgeCalibrationRunner --parallel 8

[[ -x "$RUNNER" ]] || { print -u2 "Calibration runner was not built: $RUNNER"; exit 1; }
mkdir -p "$OUT"

# Each runner invocation starts with the identical hard-tune baseline:
# Retune=0 ms, Flex=0, Humanize=0, Natural Vibrato=0. It then sweeps one
# control at a time; the preset is fixed to Alto / F# / Natural Minor by the
# runner, and both render the exact same raw WAV offline.
"$RUNNER" "$RAW" "$OUT/vibe" "VibeAutotune" "$VIBE_VST3"
"$RUNNER" "$RAW" "$OUT/artist" "Auto-Tune Artist"

python3 "$ANALYSER" "$RAW" \
  "$OUT/vibe/calibration-report.csv" \
  "$OUT/artist/calibration-report.csv" \
  "$OUT/comparison"

PYTHONPYCACHEPREFIX=/private/tmp/python-cache \
python3 "$FIT" "$RAW" \
  "$OUT/vibe/calibration-report.csv" \
  "$OUT/artist/calibration-report.csv" \
  "$OUT/transitions" \
  --pitch-tools "$ROOT/autotune/tools"

print ""
print "COMPLETE: $OUT"
print "Read first: $OUT/comparison/calibration-report.md"
print "Transitions: $OUT/transitions/transition-report.csv"
