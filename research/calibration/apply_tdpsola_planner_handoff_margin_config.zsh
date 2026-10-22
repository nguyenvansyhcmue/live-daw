#!/bin/zsh
# Adds a default-preserving, compile-time TD-PSOLA planner handoff margin
# override to the external source tree. Safe to run repeatedly.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
PATCH="/Users/hiimdrdey/autotune/vibe-tdpsola-planner-handoff-margin-config.patch"
SOURCE="$VIBE_ROOT/VibeAutotune/PluginProcessor.cpp"

[[ -f "$SOURCE" && -f "$PATCH" ]] || { print -u2 'Missing Vibe source or planner-margin patch.'; exit 66; }
if rg -q 'VIBE_TDPSOLA_PLANNER_HANDOFF_MARGIN_SAMPLES' "$SOURCE"; then
  print 'TD-PSOLA planner handoff margin configuration already installed.'
  exit 0
fi
git -C "$VIBE_ROOT" apply --check "$PATCH"
git -C "$VIBE_ROOT" apply "$PATCH"
print 'Installed TD-PSOLA planner handoff margin diagnostic hook. Default DSP behaviour is unchanged.'
