#!/bin/zsh
# Start the verified packaged DAW directly, avoiding stale LaunchServices cache.
set -euo pipefail

APP='/Users/hiimdrdey/Live daw/StudioForge Live DAW.app'
EXECUTABLE="$APP/Contents/MacOS/StudioForge DAW"
[[ -x "$EXECUTABLE" ]] || { print -u2 "Missing current StudioForge executable: $EXECUTABLE"; exit 1; }

STUDIOFORGE_AUDIO_TRACE=1 nohup "$EXECUTABLE" </dev/null \
  >>/private/tmp/studioforge-current-release.log 2>&1 &
print "Opened current StudioForge with trace enabled (pid $!)."
print 'Open the VibeAutotune editor and play/sing; trace files appear in ~/Documents/StudioForge Diagnostics/.'
