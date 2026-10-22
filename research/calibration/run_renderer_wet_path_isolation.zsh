#!/bin/zsh
# Build isolated, uninstalled Vibe VST3 candidates and bounce the user's exact
# Hook-2 segment.  This never touches the installed plug-in or packaged DAW.
set -euo pipefail

SOURCE=/Users/hiimdrdey/code/daw-autotune-local-backup-20261017-132903
DAW=/Users/hiimdrdey/code/daw
RAW='/Users/hiimdrdey/Music/Music/Media.localized/Music/Unknown Artist/Unknown Album/hook2_raw_segment.wav'
RUNNER="$DAW/build-calibration-arm64/StudioForgeCalibrationRunner"
LINEAR="$DAW/autotune/.third_party/signalsmith_linear-src"
STRETCH="$DAW/autotune/.third_party/signalsmith_stretch-src"
JUCE="$DAW/build-macos-arm64/_deps/juce-src"
ROOT="/private/tmp/vibe-renderer-wet-path-isolation-$(date +%Y%m%d-%H%M%S)"
OUT="/Users/hiimdrdey/autotune/artifacts/renderer-wet-path-isolation-$(date +%Y%m%d-%H%M%S)"
PATCH="/Users/hiimdrdey/autotune/patches/renderer-wet-path-isolation.patch"

[[ -d "$SOURCE" && -x "$RUNNER" && -f "$RAW" && -d "$LINEAR" && -d "$STRETCH" && -d "$JUCE" ]] || {
  print -u2 'Missing source, runner, raw WAV, Signalsmith dependency, or JUCE source.'
  exit 1
}

mkdir -p "$ROOT" "$OUT"
# Only build inputs.  Historic bounces/data are several GB and cannot affect
# this renderer A/B; JUCE comes from the explicitly pinned shared tree below.
rsync -a --exclude '.git' --exclude 'build*' --exclude 'VibeAutotune_artefacts' \
  --exclude 'JUCE_SDK' --exclude 'artifacts' --exclude 'renders' \
  --exclude 'artist-renders' --exclude 'data' --exclude 'archive' \
  "$SOURCE/" "$ROOT/source/"
(cd "$ROOT/source" && patch -p0 < "$PATCH")

for mode in 1 2; do
  build="$ROOT/build-$mode"
  cmake -S "$ROOT/source" -B "$build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DVIBE_JUCE_SOURCE_DIR="$JUCE" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR="$LINEAR" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH="$STRETCH" \
    -DCMAKE_CXX_FLAGS="-DVIBE_RENDERER_WET_PATH_ISOLATION=$mode"
  cmake --build "$build" --target VibeAutotune_VST3 -j 4
  vst="$build/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
  "$RUNNER" "$RAW" "$OUT/mode-$mode" VibeAutotune "$vst" | tee "$OUT/mode-$mode-runner.log"
  ditto "$vst" "$OUT/VibeAutotune-mode-$mode.vst3"
done

cat > "$OUT/README.txt" <<EOF
Renderer wet-path isolation; NOT installed.
mode-1: residual removed; lifecycle crossfade retained.
mode-2: fully wet while voiced; no dry/wet overlap.
Listen first to: mode-1/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav
Then compare:     mode-2/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav
EOF
print "COMPLETE (uninstalled): $OUT"
print "Mode 1: $OUT/mode-1/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav"
print "Mode 2: $OUT/mode-2/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav"
