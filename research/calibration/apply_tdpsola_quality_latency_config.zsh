#!/bin/zsh
set -euo pipefail
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
PATCH="/Users/hiimdrdey/autotune/vibe-tdpsola-quality-latency-config.patch"
SOURCE="$VIBE_ROOT/VibeAutotune/PluginProcessor.cpp"
[[ -f "$SOURCE" && -f "$PATCH" ]] || { print -u2 'Missing Vibe source or quality-latency patch.'; exit 66; }
if rg -q 'VIBE_TDPSOLA_LATENCY_SAMPLES' "$SOURCE"; then
  print 'TD-PSOLA quality-latency configuration already installed.'
  exit 0
fi
git -C "$VIBE_ROOT" apply --check "$PATCH"
git -C "$VIBE_ROOT" apply "$PATCH"
print 'Installed TD-PSOLA quality-latency diagnostic hook. Default DSP behaviour is unchanged.'
