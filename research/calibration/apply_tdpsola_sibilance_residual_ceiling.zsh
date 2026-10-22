#!/bin/zsh
# Adds a disabled-by-default ceiling to the existing residual path.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
PATCH="$ROOT/tdpsola-sibilance-residual-ceiling.patch"

if ! rg -q 'VIBE_TDPSOLA_CAUSAL_SIBILANCE_ENVELOPE' "$VIBE_ROOT/VibeAutotune/CausalTDPSOLARenderer.h"; then
  print -u2 'Apply the causal sibilance probe first.'
  exit 66
fi

if rg -q 'VIBE_TDPSOLA_SIBILANCE_MAX_RESIDUAL_MIX' "$VIBE_ROOT/VibeAutotune/CausalTDPSOLARenderer.h" \
   && rg -q 'sibilanceResidualTarget = std::min' "$VIBE_ROOT/VibeAutotune/CausalTDPSOLARenderer.h"; then
  print 'Sibilance residual ceiling hook already applied.'
else
  git -C "$VIBE_ROOT" apply --check "$PATCH"
  git -C "$VIBE_ROOT" apply "$PATCH"
  print 'Applied residual-ceiling hook. Default remains 1.0.'
fi
