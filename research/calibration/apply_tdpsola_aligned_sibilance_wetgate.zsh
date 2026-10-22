#!/bin/zsh
# Aligns wet-gate evidence with the delayed audio output. Default stays off.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
SOURCE="$VIBE_ROOT/VibeAutotune/CausalTDPSOLARenderer.h"
PATCH="$ROOT/tdpsola-aligned-sibilance-wetgate.patch"

if ! rg -q 'VIBE_TDPSOLA_SIBILANCE_WET_GATE_THRESHOLD' "$SOURCE"; then
  print -u2 'Apply the wet-gate hook first.'
  exit 66
fi
if rg -q 'sourceHighFrequencyEvidenceRing' "$SOURCE"; then
  print 'Aligned sibilance wet-gate hook already applied.'
else
  git -C "$VIBE_ROOT" apply --check "$PATCH"
  git -C "$VIBE_ROOT" apply "$PATCH"
  print 'Applied aligned wet-gate hook. Default threshold 2.0 keeps it disabled.'
fi
