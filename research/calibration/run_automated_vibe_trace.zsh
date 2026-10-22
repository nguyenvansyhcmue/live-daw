#!/bin/zsh
set -euo pipefail

# Launches the support-only DAW workflow built by deploy_live_audibility_hotfix.zsh.
# The app itself owns track creation, native Vibe insertion, LIVE routing and
# diagnostic tracing; this script never drives the UI by screen coordinates.
APP="${STUDIOFORGE_DEST_APP:-/Users/hiimdrdey/Live daw/StudioForge Live DAW.app}"

[[ -d "$APP" ]] || { print -u2 "StudioForge app is missing: $APP"; exit 1; }

osascript -e 'tell application id "com.StudioForge.StudioForgeDAW" to quit' 2>/dev/null || true
sleep 1
EXECUTABLE="$APP/Contents/MacOS/StudioForge DAW"
[[ -x "$EXECUTABLE" ]] || { print -u2 "StudioForge executable is missing: $EXECUTABLE"; exit 1; }

# Some locally re-signed bundles are valid on disk but stale in LaunchServices,
# which makes `open` incorrectly return kLSNoExecutableErr. Direct execution
# preserves the bundle's working directory and command-line argument without
# depending on that cache.
"$EXECUTABLE" --automated-vibe-trace >/private/tmp/studioforge-automated-vibe-trace.log 2>&1 &
print "StudioForge opened in automated Vibe trace mode. Speak or play the vocal source; CSV is written under ~/Documents/StudioForge Diagnostics/."
