#!/bin/zsh
# A/B only: aligns transient evidence to the renderer's latency before gating.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
export VIBE_SIBILANCE_WETGATE_ALIGNED=1
export VIBE_SIBILANCE_WETGATE_BUILD="${VIBE_SIBILANCE_WETGATE_BUILD:-/Users/hiimdrdey/code/daw/autotune/build-hook2-tdpsola-aligned-sibilance-wetgate004}"
export VIBE_SIBILANCE_WETGATE_OUT_PREFIX="hook2-tdpsola-aligned-sibilance-wetgate004"
exec zsh "$ROOT/run_hook2_tdpsola_sibilance_wetgate004_host_ab.zsh"
