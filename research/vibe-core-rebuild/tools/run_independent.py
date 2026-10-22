"""Render natural-key holdouts through the corrected StudioForge host.

References are archived licensed Artist bounces, NOT freshly verified renders.
Never install a plug-in or modify the reference tree.
"""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
data = Path('/Users/hiimdrdey/Library/Application Support/StudioForge/Research/GTSinger')
archive = data / 'runs/artist-vibe-ab-20261018-123937'
entries = json.loads((data / 'vibe-gtsinger-ab-test-plan.json').read_text())['entries']
out = root / 'results/independent'
out.mkdir(parents=True, exist_ok=True)
wave = 'case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav'
rows = list(csv.DictReader((archive / 'run-index.csv').open()))
summary = []
for row in rows:
    if row['group'] == 'Control_Group' or row['artist_key'] not in ['C', 'F']:
        continue
    entry = next(e for e in entries if all(e[k] == row[k] for k in
                 ['dataset_voice', 'technique', 'song', 'clip', 'group']))
    reference = Path(row['comparison']).parents[1] / 'artist' / wave
    name = reference.parents[1].name
    dest = out / name
    dest.mkdir(exist_ok=True)
    candidate = dest / 'vibe' / wave
    env = dict(os.environ, STUDIOFORGE_CALIBRATION_VOICE=row['vibe_voice'],
               STUDIOFORGE_CALIBRATION_KEY=row['vibe_key'],
               STUDIOFORGE_CALIBRATION_SCALE=row['scale'])
    if not candidate.exists():
        with (dest / 'render.log').open('w') as log:
            subprocess.run([str(root/'build/StudioForgeReferenceRunner'), entry['input_wav'],
                str(dest/'vibe'), 'VibeAutotune',
                str(root/'build/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3')],
                env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    with (dest / 'analysis.log').open('w') as log:
        subprocess.run([sys.executable, str(root/'tools/measure_candidate.py'), entry['input_wav'],
            str(reference), str(candidate), str(dest/'audit')], stdout=log, stderr=subprocess.STDOUT, check=True)
    metrics = json.loads((dest/'audit/metrics.json').read_text())
    summary.append(dict(name=name, voice=row['vibe_voice'], key=row['vibe_key'], scale=row['scale'],
                        reference_status='archived; not re-rendered in this session',
                        **metrics['whole']))
    print(json.dumps(summary[-1]), flush=True)
(out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
