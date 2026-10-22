"""Run the existing annotation-based meter on independent natural-key clips."""
import json
from pathlib import Path
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
for metrics in sorted((root/'results/independent').glob('*/audit/metrics.json')):
    m=json.loads(metrics.read_text());raw=Path(m['provenance']['raw']['path'])
    grid=raw.with_suffix('.TextGrid')
    if not grid.exists():grid=raw.with_name(raw.stem+'_TextGrid')
    if not grid.exists():continue
    output=metrics.parent/'consonants.csv'
    with (metrics.parent/'consonants.log').open('w') as log:
        result=subprocess.run([sys.executable,'/Users/hiimdrdey/autotune/tools/measure_annotated_consonant_alignment.py',
            '--raw',str(raw),'--artist',m['provenance']['artist']['path'],
            '--vibe',m['provenance']['candidate']['path'],'--textgrid',str(grid),'--output',str(output)],
            stdout=log,stderr=subprocess.STDOUT)
    print(metrics.parent.parent.name,result.returncode,flush=True)
