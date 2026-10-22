#!/bin/zsh
set -euo pipefail

# Canonical Logic Pro deployment. The underlying deployer builds the current
# Release VibeAutotune source, verifies the AU binary after installation, and
# resets Audio Unit registration. Keeping Logic closed is essential: it holds
# an in-process copy of an AU until the host quits.
SCRIPT_DIR="${0:A:h}"

osascript -e 'tell application "Logic Pro" to quit' 2>/dev/null || true
sleep 3

STUDIOFORGE_SKIP_OPEN=1 zsh "$SCRIPT_DIR/deploy_latest_vibeautotune_to_daw.zsh"

killall -9 AudioComponentRegistrar 2>/dev/null || true
open -a "Logic Pro"

print "Logic Pro opened with the verified current Release VibeAutotune AU."
