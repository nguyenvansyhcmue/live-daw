#!/bin/zsh
# Host-level confirmation for the uninstalled Tenor 128-sample analysis-hop
# candidate.  It deliberately renders only the two already-qualified Tenor
# vibrato clips, reuses Artist bounces, and never installs/replaces a plug-in.
set -euo pipefail

workspace="${GTSINGER_WORKSPACE:-/Users/hiimdrdey/autotune}"
research_root="${GTSINGER_BENCHMARK_ROOT:-$HOME/Library/Application Support/StudioForge/Research/GTSinger}"
daw_root="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
runner="${STUDIOFORGE_CALIBRATION_RUNNER:-$daw_root/build-macos-arm64/StudioForgeCalibrationRunner}"
analyser="$daw_root/Tools/analyze_studioforge_calibration.py"
tools="${PITCH_TOOLS:-$workspace/artifacts/crossing24-bounded-preview-20261017-113341/source/tools}"
reference_run="${GTSINGER_ARTIST_REFERENCE_RUN:-$research_root/runs/artist-vibe-ab-20261018-123937}"
candidate="${VIBE_CANDIDATE_VST3:-$workspace/artifacts/crossing24-bounded-preview-20261017-113341/source/build-tenor-vibrato-hop128-probe/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3}"
output="${GTSINGER_HOST_OUTPUT:-${GTSINGER_HOP128_OUTPUT:-$workspace/artifacts/gtsinger-tenor-vibrato-host-$(date +%Y%m%d-%H%M%S)}}"

[[ -x "$runner" && -f "$analyser" ]] || { print -u2 'Missing StudioForge calibration runner or analyzer.'; exit 66; }
[[ -x "$candidate/Contents/MacOS/VibeAutotune" ]] || { print -u2 "Missing VST3 candidate: $candidate"; exit 66; }
[[ -f "$reference_run/jobs.tsv" ]] || { print -u2 "Missing reference jobs: $reference_run/jobs.tsv"; exit 66; }
[[ -f "$tools/compare_pitch_correction_bounces.py" && -f "$tools/measure_artist_vibe_latency_aligned.py" ]] || {
  print -u2 'Missing pinned pitch-analysis tools.'; exit 66
}
mkdir -p "$output"

RUNNER="$runner" CANDIDATE="$candidate/Contents/MacOS/VibeAutotune" REFERENCE="$reference_run" ANALYSER="$analyser" TOOLS="$tools" OUT="$output" python3 - <<'PY'
import hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

def digest(value):
    path = Path(value)
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return {'path': str(path), 'sha256': h.hexdigest(), 'bytes': path.stat().st_size}

out = Path(os.environ['OUT'])
provenance = out / 'provenance.json'
payload = {
    'schema': 1,
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'purpose': 'host confirmation of uninstalled Tenor analysis-hop VST3 candidate',
    'scope': ['EN-Tenor-1 / Vibrato / Control_Group', 'EN-Tenor-1 / Vibrato / Vibrato_Group'],
    'runner': digest(os.environ['RUNNER']),
    'candidate_binary': digest(os.environ['CANDIDATE']),
    'reference_jobs': digest(Path(os.environ['REFERENCE']) / 'jobs.tsv'),
    'analyser': digest(os.environ['ANALYSER']),
    'pitch_tools': {name: digest(Path(os.environ['TOOLS']) / name) for name in (
        'compare_pitch_correction_bounces.py', 'measure_artist_vibe_latency_aligned.py')},
}
if provenance.exists():
    old = json.loads(provenance.read_text())
    for key in ('runner', 'candidate_binary', 'reference_jobs', 'analyser', 'pitch_tools'):
        if old.get(key) != payload[key]:
            raise SystemExit(f'Refusing to resume with changed provenance: {key}; use a new output directory')
else:
    provenance.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
PY

print 'dataset_voice,vibe_voice,technique,song,clip,group,key,scale,status,comparison' > "$output/run-index.csv"

awk -F $'\t' 'NR == 1 || ($1 == "EN-Tenor-1" && $4 == "Vibrato" && ($7 == "Control_Group" || $7 == "Vibrato_Group"))' "$reference_run/jobs.tsv" |
tail -n +2 | while IFS=$'\t' read -r dataset_voice vibe_voice artist_voice technique song clip group vibe_key artist_key scale input; do
  safe_song="${song//[^[:alnum:]]/_}"
  name="${dataset_voice}-${technique}-${safe_song}-${clip}-${group}"
  reference="$reference_run/$name/artist/calibration-report.csv"
  job="$output/$name"
  [[ -f "$input" && -f "$reference" ]] || { print -u2 "Missing input or Artist reference for $name"; exit 66; }
  mkdir -p "$job/vibe"
  if [[ -f "$job/vibe/calibration-report.csv" ]]; then
    REPORT="$job/vibe/calibration-report.csv" python3 - <<'PY'
import csv, os
from pathlib import Path
report = Path(os.environ['REPORT'])
with report.open(newline='') as f:
    rows = list(csv.DictReader(f))
try:
    cases = {int(row['case']) for row in rows}
    valid = len(rows) == 24 and cases == set(range(24)) and all(Path(row['output']).is_file() for row in rows)
except (ValueError, KeyError, TypeError):
    valid = False
if not valid:
    raise SystemExit(f'Incomplete render in {report}; use a fresh output directory')
PY
  else
    print "[$dataset_voice | $technique | $group] host render: Tenor/C/Major, VST3=$candidate"
    env STUDIOFORGE_CALIBRATION_VOICE=Tenor STUDIOFORGE_CALIBRATION_KEY=C STUDIOFORGE_CALIBRATION_SCALE=Major \
      "$runner" "$input" "$job/vibe" VibeAutotune "$candidate" > "$job/runner.log" 2>&1 || {
        print -u2 "Candidate render failed; read $job/runner.log"; exit 1
      }
  fi
  rg -q 'name="VibeAutotune" format="VST3"' "$job/vibe/StudioForgeCalibrationPluginCatalog.xml" || {
    print -u2 "Candidate catalog did not confirm VST3 for $name"; exit 1
  }
  PYTHONPATH="$tools${PYTHONPATH:+:$PYTHONPATH}" PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$analyser" \
    "$input" "$job/vibe/calibration-report.csv" "$reference" "$job/comparison"
  print -r -- "$dataset_voice,$vibe_voice,$technique,$song,$clip,$group,$vibe_key,$scale,pass,$job/comparison/calibration-report.md" >> "$output/run-index.csv"
done

PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$workspace/gtsinger_benchmark/summarize_gtsinger_ab.py" \
  "$output" --output "$output/hard-tune-zero-summary.md"

print ''
print "HOST A/B COMPLETE (not installed): $output"
print "Summary: $output/hard-tune-zero-summary.md"
print "Provenance: $output/provenance.json"
