#!/bin/zsh
# Render an uninstalled VST3 candidate against the Artist references from one
# completed GTSinger run.  This deliberately never touches the installed AU.
set -euo pipefail

workspace="${GTSINGER_WORKSPACE:-/Users/hiimdrdey/autotune}"
research_root="${GTSINGER_BENCHMARK_ROOT:-$HOME/Library/Application Support/StudioForge/Research/GTSinger}"
daw_root="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
runner="${STUDIOFORGE_CALIBRATION_RUNNER:-$daw_root/build-macos-arm64/StudioForgeCalibrationRunner}"
analyser="$daw_root/Tools/analyze_studioforge_calibration.py"
tools="${PITCH_TOOLS:-$workspace/artifacts/crossing24-bounded-preview-20261017-113341/source/tools}"
reference_run="${GTSINGER_ARTIST_REFERENCE_RUN:-$research_root/runs/artist-vibe-ab-20261018-123937}"
candidate="${VIBE_CANDIDATE_VST3:-$workspace/artifacts/crossing24-bounded-preview-20261017-113341/source/build-hook2-tdpsola-crossing-24/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3}"
output="${GTSINGER_EXPLICIT_OUTPUT:-$workspace/artifacts/gtsinger-tdpsola-cross-singer-$(date +%Y%m%d-%H%M%S)}"

[[ -x "$runner" && -f "$analyser" ]] || { print -u2 'Missing StudioForge calibration runner or analyzer.'; exit 66; }
zsh "$workspace/gtsinger_benchmark/require_key_aware_runner.zsh" "$runner" "$daw_root/Source/Services/StudioForgeCalibrationRunner.cpp"
[[ -x "$candidate/Contents/MacOS/VibeAutotune" ]] || { print -u2 "Missing VST3 candidate: $candidate"; exit 66; }
[[ -f "$reference_run/jobs.tsv" && -f "$reference_run/run-index.csv" ]] || { print -u2 "Invalid completed reference run: $reference_run"; exit 66; }
[[ -f "$tools/compare_pitch_correction_bounces.py" && -f "$tools/measure_artist_vibe_latency_aligned.py" ]] || {
  print -u2 'Missing pinned pitch-analysis tools.'; exit 66
}
mkdir -p "$output"

RUNNER="$runner" CANDIDATE="$candidate/Contents/MacOS/VibeAutotune" REFERENCE="$reference_run" ANALYSER="$analyser" TOOLS="$tools" OUT="$output" python3 - <<'PY'
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

def digest(value):
    path = Path(value)
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return {'path': str(path), 'sha256': h.hexdigest(), 'bytes': path.stat().st_size}

payload = {
    'schema': 1,
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'purpose': 'uninstalled explicit VST3 candidate versus existing Artist bounces',
    'runner': digest(os.environ['RUNNER']),
    'candidate_binary': digest(os.environ['CANDIDATE']),
    'reference_jobs': digest(Path(os.environ['REFERENCE']) / 'jobs.tsv'),
    'reference_index': digest(Path(os.environ['REFERENCE']) / 'run-index.csv'),
    'analyser': digest(os.environ['ANALYSER']),
    'pitch_tools': {name: digest(Path(os.environ['TOOLS']) / name) for name in (
        'compare_pitch_correction_bounces.py', 'measure_artist_vibe_latency_aligned.py')},
}
Path(os.environ['OUT'], 'provenance.json').write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
PY

[[ -f "$output/run-index.csv" ]] || print 'dataset_voice,vibe_voice,artist_voice,technique,song,clip,group,vibe_key,artist_key,scale,status,comparison' > "$output/run-index.csv"

tail -n +2 "$reference_run/jobs.tsv" | while IFS=$'\t' read -r dataset_voice vibe_voice artist_voice technique song clip group vibe_key artist_key scale input; do
  safe_song="${song//[^[:alnum:]]/_}"
  name="${dataset_voice}-${technique}-${safe_song}-${clip}-${group}"
  reference="$reference_run/$name/artist/calibration-report.csv"
  job="$output/$name"
  [[ -f "$input" && -f "$reference" ]] || { print -u2 "Missing input or Artist reference for $name"; exit 66; }
  mkdir -p "$job/vibe"
  if [[ ! -f "$job/vibe/calibration-report.csv" ]]; then
    print "[$dataset_voice | $technique | $group | $song | $clip] VST3=$candidate"
    env STUDIOFORGE_CALIBRATION_VOICE="$vibe_voice" STUDIOFORGE_CALIBRATION_KEY="$vibe_key" STUDIOFORGE_CALIBRATION_SCALE="$scale" \
      "$runner" "$input" "$job/vibe" VibeAutotune "$candidate" > "$job/runner.log" 2>&1 || {
        print -u2 "Candidate render failed; read $job/runner.log"; exit 1
      }
  else
    print "[$dataset_voice | $technique | $group | $song | $clip] reusing explicit VST3 bounce"
  fi
  rg -q 'name="VibeAutotune" format="VST3"' "$job/vibe/StudioForgeCalibrationPluginCatalog.xml" || {
    print -u2 "Candidate catalog did not confirm VST3 for $name"; exit 1
  }
  if [[ ! -f "$job/comparison/calibration-report.md" ]]; then
    PYTHONPATH="$tools${PYTHONPATH:+:$PYTHONPATH}" PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$analyser" \
      "$input" "$job/vibe/calibration-report.csv" "$reference" "$job/comparison"
  fi
  if ! rg -Fq "$job/comparison/calibration-report.md" "$output/run-index.csv"; then
    print -r -- "$dataset_voice,$vibe_voice,$artist_voice,$technique,$song,$clip,$group,$vibe_key,$artist_key,$scale,pass,$job/comparison/calibration-report.md" >> "$output/run-index.csv"
  fi
done

PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$workspace/gtsinger_benchmark/summarize_gtsinger_ab.py" \
  "$output" --output "$output/hard-tune-zero-summary.md"

print ''
print "EXPLICIT VST3 A/B COMPLETE (not installed): $output"
print "Summary: $output/hard-tune-zero-summary.md"
print "Provenance: $output/provenance.json"
