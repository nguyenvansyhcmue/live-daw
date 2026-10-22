#!/bin/zsh
set -euo pipefail
root="${GTSINGER_BENCHMARK_ROOT:-$HOME/Library/Application Support/StudioForge/Research/GTSinger}"
script_dir="${0:A:h}"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$script_dir/build_gtsinger_test_plan.py" \
  "$root/vibe-gtsinger-research-manifest.json" \
  --output "$root/vibe-gtsinger-ab-test-plan.json"
