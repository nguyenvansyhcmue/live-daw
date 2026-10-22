#!/bin/zsh
# Uses existing fixed renderer latency for optional bounded transient lookahead.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
SOURCE="$VIBE_ROOT/VibeAutotune/CausalTDPSOLARenderer.h"
PATCH="$ROOT/tdpsola-sibilance-wetgate-lookahead.patch"

if ! rg -q 'sourceHighFrequencyEvidenceRing' "$SOURCE"; then
  print -u2 'Apply the aligned wet-gate hook first.'
  exit 66
fi
if rg -q 'VIBE_TDPSOLA_SIBILANCE_WET_GATE_LOOKAHEAD_SAMPLES' "$SOURCE"; then
  print 'Sibilance wet-gate lookahead hook already applied.'
else
  git -C "$VIBE_ROOT" apply --check "$PATCH"
  git -C "$VIBE_ROOT" apply "$PATCH"
  print 'Applied wet-gate lookahead hook. Default remains zero samples.'
fi
