#!/bin/zsh
# Guard per-clip A/B runs against the obsolete fixed-F# calibration binary.
set -euo pipefail

runner="${1:?calibration runner path required}"
source_file="${2:?calibration runner source path required}"
[[ -x "$runner" && -f "$source_file" ]] || {
  print -u2 "Missing calibration runner or its source: $runner / $source_file"
  exit 66
}
if ! strings "$runner" | rg 'STUDIOFORGE_CALIBRATION_KEY' >/dev/null; then
  print -u2 "Calibration runner does not support per-clip key/scale: $runner"
  exit 65
fi
if [[ "$source_file" -nt "$runner" ]]; then
  print -u2 "Calibration runner is older than its source; rebuild before A/B: $runner"
  exit 65
fi
