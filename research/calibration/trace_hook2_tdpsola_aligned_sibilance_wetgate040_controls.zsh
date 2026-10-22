#!/bin/zsh
# Read-only potential-gate trace: .40 keeps normal wet path intact.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
export VIBE_CAUSAL_SIBILANCE_BUILD="${VIBE_CAUSAL_SIBILANCE_BUILD:-/Users/hiimdrdey/code/daw/autotune/build-hook2-tdpsola-aligned-sibilance-wetgate040}"
exec zsh "$ROOT/trace_hook2_tdpsola_causal_sibilance_controls.zsh"
