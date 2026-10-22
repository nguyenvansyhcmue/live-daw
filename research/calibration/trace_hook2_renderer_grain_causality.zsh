#!/bin/zsh
# Read-only causal audit using timestamped TD-PSOLA telemetry.
set -euo pipefail
ROOT="/Users/hiimdrdey/autotune"
CASE="${HOOK2_CASE:-$ROOT/artifacts/hook2-adjacent-dwell-sweep-20261016-034136/dwell_80ms}"
OUT="$ROOT/artifacts/hook2-renderer-grain-causality-$(date +%Y%m%d-%H%M%S)"
[[ -f "$CASE/full_default_intervals.csv" ]] || { print -u2 "Missing trace: $CASE/full_default_intervals.csv"; exit 2; }
python3 "$ROOT/audit_renderer_grain_causality.py" "$CASE/full_default_intervals.csv" "$OUT"
printf '\nTRACE COMPLETE (read-only; not installed): %s\n' "$OUT"
printf 'Read: %s/grain-causality-report.md\n' "$OUT"
