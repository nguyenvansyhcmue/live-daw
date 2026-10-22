#!/bin/zsh
# Run an external, reproducible Artist/Vibe A/B batch from the locked GTSinger
# plan. Derived bounces remain outside the source repository.
set -euo pipefail

root="${GTSINGER_BENCHMARK_ROOT:-$HOME/Library/Application Support/StudioForge/Research/GTSinger}"
script_dir="${0:A:h}"
daw_root="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
runner="${STUDIOFORGE_CALIBRATION_RUNNER:-$daw_root/build-macos-arm64/StudioForgeCalibrationRunner}"
analyser="$daw_root/Tools/analyze_studioforge_calibration.py"
plan="$root/vibe-gtsinger-ab-test-plan.json"
pair_count="${GTSINGER_PAIRS_PER_TECHNIQUE:-1}"
stamp="$(date +%Y%m%d-%H%M%S)"
out="${GTSINGER_RUN_ROOT:-$root/runs/artist-vibe-ab-$stamp}"
vibe_query="${VIBE_QUERY:-VibeAutotune}"
artist_query="${ARTIST_QUERY:-Auto-Tune Artist}"
# The current monorepo migration archived these analysis helpers in the last
# verified source snapshot. Pin the snapshot rather than silently importing a
# random tool version from PYTHONPATH.
pitch_tools="${PITCH_TOOLS:-/Users/hiimdrdey/autotune/artifacts/crossing24-bounded-preview-20261017-113341/source/tools}"

[[ -x "$runner" ]] || { print -u2 "Missing runner: $runner"; exit 66; }
zsh "$script_dir/require_key_aware_runner.zsh" "$runner" "$daw_root/Source/Services/StudioForgeCalibrationRunner.cpp"
[[ -f "$analyser" && -f "$plan" ]] || { print -u2 'Missing analyzer or key-aware test plan.'; exit 66; }
[[ -f "$pitch_tools/compare_pitch_correction_bounces.py" && -f "$pitch_tools/measure_artist_vibe_latency_aligned.py" ]] || {
  print -u2 "Missing pinned pitch-analysis tools: $pitch_tools"; exit 66
}
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$script_dir/verify_gtsinger_plan.py" "$plan"
mkdir -p "$out"
[[ -f "$out/test-plan.json" ]] || cp "$plan" "$out/test-plan.json"
# A batch is only useful for DSP decisions when its executable and the
# installed AU candidates can be identified later.  The runner's plug-in
# catalog records the AU component/version, but not the binary digest.  Keep
# an immutable, read-only snapshot here; this never installs or modifies a
# plug-in.
if [[ ! -f "$out/provenance.json" ]]; then
  RUNNER="$runner" PLAN="$plan" ANALYSER="$analyser" PITCH_TOOLS="$pitch_tools" OUT="$out" python3 - <<'PY'
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

def digest(path):
    path = Path(path)
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return {'path': str(path), 'sha256': h.hexdigest(), 'bytes': path.stat().st_size}

home = Path.home()
au_roots = [
    home / 'Library/Audio/Plug-Ins/Components/VibeAutotune.component',
    Path('/Library/Audio/Plug-Ins/Components/VibeAutotune.component'),
]
payload = {
    'schema': 1,
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'host_platform': platform.platform(),
    'runner': digest(os.environ['RUNNER']),
    'test_plan': digest(os.environ['PLAN']),
    'analyser': digest(os.environ['ANALYSER']),
    'pitch_tools': {
        name: digest(Path(os.environ['PITCH_TOOLS']) / name)
        for name in ('compare_pitch_correction_bounces.py',
                     'measure_artist_vibe_latency_aligned.py')
    },
    # These are candidates visible at batch start.  AudioUnit discovery is
    # still confirmed by each job's PluginCatalog XML.
    'vibe_audio_unit_candidates': [
        digest(root / 'Contents/MacOS/VibeAutotune') for root in au_roots
        if (root / 'Contents/MacOS/VibeAutotune').is_file()
    ],
}
Path(os.environ['OUT'], 'provenance.json').write_text(
    json.dumps(payload, indent=2, sort_keys=True) + '\n')
PY
fi
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$script_dir/emit_gtsinger_jobs.py" "$plan" --pairs-per-technique "$pair_count" > "$out/jobs.tsv"
[[ -f "$out/run-index.csv" ]] || print 'dataset_voice,vibe_voice,artist_voice,technique,song,clip,group,vibe_key,artist_key,scale,status,comparison' > "$out/run-index.csv"

tail -n +2 "$out/jobs.tsv" | while IFS=$'\t' read -r dataset_voice vibe_voice artist_voice technique song clip group vibe_key artist_key scale input; do
  safe_song="${song//[^[:alnum:]]/_}"
  job="$out/${dataset_voice}-${technique}-${safe_song}-${clip}-${group}"
  mkdir -p "$job/vibe" "$job/artist"
  print "[$dataset_voice | Vibe=$vibe_voice Artist=$artist_voice | $technique | $group | $song | $clip] VibeKey=$vibe_key ArtistKey=$artist_key $scale"
  if [[ ! -f "$job/vibe/calibration-report.csv" ]]; then
    env STUDIOFORGE_CALIBRATION_VOICE="$vibe_voice" STUDIOFORGE_CALIBRATION_KEY="$vibe_key" STUDIOFORGE_CALIBRATION_SCALE="$scale" \
      "$runner" "$input" "$job/vibe" "$vibe_query"
  else
    print '  reusing existing Vibe bounce report'
  fi
  if [[ ! -f "$job/artist/calibration-report.csv" ]]; then
    env STUDIOFORGE_CALIBRATION_VOICE="$artist_voice" STUDIOFORGE_CALIBRATION_KEY="$artist_key" STUDIOFORGE_CALIBRATION_SCALE="$scale" \
      "$runner" "$input" "$job/artist" "$artist_query"
  else
    print '  reusing existing Artist bounce report'
  fi
  if [[ ! -f "$job/comparison/calibration-report.md" ]]; then
    PYTHONPATH="$pitch_tools${PYTHONPATH:+:$PYTHONPATH}" PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$analyser" \
      "$input" "$job/vibe/calibration-report.csv" "$job/artist/calibration-report.csv" "$job/comparison"
  else
    print '  reusing existing comparison report'
  fi
  if ! rg -Fq "$job/comparison/calibration-report.md" "$out/run-index.csv"; then
    print -r -- "$dataset_voice,$vibe_voice,$artist_voice,$technique,$song,$clip,$group,$vibe_key,$artist_key,$scale,pass,$job/comparison/calibration-report.md" >> "$out/run-index.csv"
  fi
done

PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$script_dir/summarize_gtsinger_ab.py" \
  "$out" --output "$out/hard-tune-zero-summary.md"

print ''
print "A/B batch complete: $out"
print "Index: $out/run-index.csv"
print "Summary: $out/hard-tune-zero-summary.md"
print 'This batch is diagnostic only; it does not install, sign, or replace any plug-in.'
