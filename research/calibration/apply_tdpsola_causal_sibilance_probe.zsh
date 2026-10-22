#!/bin/zsh
# Adds a disabled-by-default, realtime-safe causal high-band detector.
# The following A/B enables it only in an isolated build; no installed bundle
# changes. A semantic source marker is used instead of reverse-applying the
# full patch: later experiments may legitimately edit the same renderer.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
PATCH="$ROOT/tdpsola-causal-sibilance-envelope.patch"

[[ -f "$VIBE_ROOT/VibeAutotune/CausalTDPSOLARenderer.h" ]] || { print -u2 "Missing Vibe source"; exit 66; }
if rg -q 'VIBE_TDPSOLA_CAUSAL_SIBILANCE_ENVELOPE' "$VIBE_ROOT/VibeAutotune/CausalTDPSOLARenderer.h" \
   && rg -q 'sourceHighpassLowState' "$VIBE_ROOT/VibeAutotune/CausalTDPSOLARenderer.h"; then
  print "Causal sibilance-envelope probe already applied."
else
  git -C "$VIBE_ROOT" apply --check "$PATCH"
  git -C "$VIBE_ROOT" apply "$PATCH"
  print "Applied causal sibilance-envelope probe. Default remains OFF."
fi
