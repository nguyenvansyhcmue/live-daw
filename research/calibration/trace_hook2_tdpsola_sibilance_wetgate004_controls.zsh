#!/bin/zsh
# Trace only the compiled wet-gate candidate; does not build or install VST3.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
export VIBE_CAUSAL_SIBILANCE_BUILD="${VIBE_CAUSAL_SIBILANCE_BUILD:-/Users/hiimdrdey/code/daw/autotune/build-hook2-tdpsola-sibilance-wetgate004}"

exec zsh "$ROOT/trace_hook2_tdpsola_causal_sibilance_controls.zsh"
