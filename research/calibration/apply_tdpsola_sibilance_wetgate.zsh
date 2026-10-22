#!/bin/zsh
# Adds a default-disabled wet-path transient gate after the causal detector.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
PATCH="$ROOT/tdpsola-sibilance-wetgate.patch"
SOURCE="$VIBE_ROOT/VibeAutotune/CausalTDPSOLARenderer.h"

if ! rg -q 'VIBE_TDPSOLA_CAUSAL_SIBILANCE_ENVELOPE' "$SOURCE"; then
  print -u2 'Apply the causal sibilance detector first.'
  exit 66
fi
if rg -q 'VIBE_TDPSOLA_SIBILANCE_WET_GATE_THRESHOLD' "$SOURCE"; then
  print 'Sibilance wet-gate hook already applied.'
else
  git -C "$VIBE_ROOT" apply --check "$PATCH"
  git -C "$VIBE_ROOT" apply "$PATCH"
  print 'Applied wet-gate hook. Default threshold 2.0 keeps it disabled.'
fi
