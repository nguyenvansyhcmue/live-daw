#!/bin/zsh
# Read-only provenance trace for the aligned wet-gate .04 candidate.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
export VIBE_CAUSAL_SIBILANCE_BUILD="${VIBE_CAUSAL_SIBILANCE_BUILD:-/Users/hiimdrdey/code/daw/autotune/build-hook2-tdpsola-aligned-sibilance-wetgate004}"
exec zsh "$ROOT/trace_hook2_tdpsola_causal_sibilance_controls.zsh"
