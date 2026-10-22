#!/bin/zsh
# Adds a diagnostic-only Natural Vibrato hard-tune blend (default 0), builds
# it, then compares five candidate weights against the frozen Artist trace.
set -euo pipefail
DAW=/Users/hiimdrdey/code/daw
VIBE_SOURCE="$DAW/autotune"
VIBE_BUILD="$VIBE_SOURCE/build-studioforge-juce8-stable"
CAL_BUILD="$DAW/build-calibration-arm64"
RAW='/Users/hiimdrdey/Downloads/hook 2raw.wav'
ARTIST='/Users/hiimdrdey/autotune/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv'
ANALYSER="$DAW/Tools/analyze_studioforge_calibration.py"
PATCH_VIBE='/Users/hiimdrdey/autotune/natural_hardtune_surface_diagnostic.patch'
PATCH_RUNNER='/Users/hiimdrdey/autotune/studioforge_natural_hardtune_runner.patch'
STAMP=$(date +%Y%m%d-%H%M%S)
OUT="/Users/hiimdrdey/autotune/artifacts/natural-hardtune-surface-$STAMP"

for required in "$RAW" "$ARTIST" "$PATCH_VIBE" "$PATCH_RUNNER"; do [[ -e "$required" ]] || { print -u2 "Missing: $required"; exit 1; }; done
apply_once () {
  local root=$1 patch=$2
  cd "$root"
  if git apply --reverse --check "$patch" >/dev/null 2>&1; then
    print "Already applied: ${patch:t}"
  else
    git apply --check "$patch" && git apply "$patch"
    print "Applied: ${patch:t}"
  fi
}
apply_once "$VIBE_SOURCE" "$PATCH_VIBE"
apply_once "$DAW" "$PATCH_RUNNER"

cmake --build "$VIBE_BUILD" --target VibeAutotune_VST3 --parallel 8
cmake --build "$CAL_BUILD" --target StudioForgeCalibrationRunner --parallel 8
RUNNER="$CAL_BUILD/StudioForgeCalibrationRunner"
VST3="$VIBE_BUILD/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
mkdir -p "$OUT"
for weight in 0 .25 .50 .75 1; do
  id="weight-${weight//./_}"; dir="$OUT/$id"; mkdir -p "$dir/vibe"
  VIBE_DIAG_NATURAL_HARD_TUNE_SURFACE="$weight" \
    "$RUNNER" "$RAW" "$dir/vibe" VibeAutotune "$VST3" > "$dir/runner.log"
  python3 "$ANALYSER" "$RAW" "$dir/vibe/calibration-report.csv" "$ARTIST" "$dir/comparison" >/dev/null
  print "$id:"
  grep '| 3 |\| 4 |\| 5 |\| 6 |\| 7 |' "$dir/comparison/calibration-report.md" || true
done
print "COMPLETE: $OUT"
