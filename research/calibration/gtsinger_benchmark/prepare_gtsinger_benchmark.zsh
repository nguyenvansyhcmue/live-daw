#!/bin/zsh
set -euo pipefail

root="${GTSINGER_BENCHMARK_ROOT:-$HOME/Library/Application Support/StudioForge/Research/GTSinger}"
script_dir="${0:A:h}"
if ! python3 -c 'import huggingface_hub' >/dev/null 2>&1; then
  print 'Installing the public Hugging Face client used to retrieve the selected research fixture…'
  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    python3 -m pip install 'huggingface_hub>=0.25'
  else
    python3 -m pip install --user 'huggingface_hub>=0.25'
  fi
fi
voices="${GTSINGER_VOICES:-EN-Alto-1}"
voice_args=()
for voice in ${(s:,:)voices}; do
  voice_args+=(--voice "$voice")
done
python3 "$script_dir/acquire_gtsinger_subset.py" --root "$root" --pairs-per-technique "${GTSINGER_PAIRS_PER_TECHNIQUE:-2}" --clips-per-pair "${GTSINGER_CLIPS_PER_PAIR:-4}" "${voice_args[@]}" --accept-license
