#!/bin/zsh
# A/B only: 13.3 ms lookahead inside existing renderer latency, strong /s/ gate.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
export VIBE_SIBILANCE_WETGATE_ALIGNED=1
export VIBE_SIBILANCE_WETGATE_LOOKAHEAD=1
export VIBE_SIBILANCE_WETGATE_BUILD="${VIBE_SIBILANCE_WETGATE_BUILD:-/Users/hiimdrdey/code/daw/autotune/build-hook2-tdpsola-lookahead-sibilance-wetgate040-l640}"
export VIBE_SIBILANCE_WETGATE_OUT_PREFIX="hook2-tdpsola-lookahead-sibilance-wetgate040-l640"
export VIBE_SIBILANCE_WET_GATE_THRESHOLD=0.40
export VIBE_SIBILANCE_WET_GATE_LOOKAHEAD_SAMPLES=640
exec zsh "$ROOT/run_hook2_tdpsola_sibilance_wetgate004_host_ab.zsh"
