#!/bin/zsh
set -euo pipefail

# Verifies the packaged Vibe plug-in through StudioForge's actual AudioEngine
# monitor path. It does not use StudioForgeCalibrationRunner.
ROOT=/Users/hiimdrdey/code/daw
BUILD="$ROOT/build-macos-tests"
PATCH=/Users/hiimdrdey/autotune/studioforge_embedded_vibe_signal_path.patch
APP='/Users/hiimdrdey/Live daw/StudioForge Live DAW.app'
VIBE="$APP/Contents/Resources/PlugIns/VST3/VibeAutotune.vst3"
WAV='/Users/hiimdrdey/Downloads/hook 2raw.wav'
RESULT_ROOT=/Users/hiimdrdey/autotune/artifacts
STAMP=$(date +%Y%m%d-%H%M%S)
RESULT="$RESULT_ROOT/studioforge-embedded-vibe-path-$STAMP"

[[ -d "$ROOT" && -f "$PATCH" ]] || { print -u2 'StudioForge source or signal-path patch is missing.'; exit 1; }
[[ -d "$VIBE" ]] || { print -u2 "Packaged Vibe is missing: $VIBE"; exit 1; }
[[ -f "$WAV" ]] || { print -u2 "Input WAV is missing: $WAV"; exit 1; }

cd "$ROOT"
if git apply --reverse --check "$PATCH" >/dev/null 2>&1; then
  print 'Already applied: embedded Vibe signal-path test'
else
  git apply --check "$PATCH"
  git apply "$PATCH"
  print 'Applied: embedded Vibe signal-path test'
fi

cmake --build "$BUILD" --target StudioForgeCoreTests --parallel 8
mkdir -p "$RESULT/work"
(
  cd "$RESULT/work"
  STUDIOFORGE_VIBE_SIGNAL_PATH="$VIBE" \
  STUDIOFORGE_VIBE_SIGNAL_WAV="$WAV" \
  "$BUILD/StudioForgeCoreTests"
) 2>&1 | tee "$RESULT/trace.log"

print ''
print "COMPLETE: $RESULT"
print "Read: $RESULT/trace.log"
