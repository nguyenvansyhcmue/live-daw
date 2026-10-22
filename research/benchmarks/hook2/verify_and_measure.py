"""Verify bundled evidence; optionally recompute metrics without any audio host."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

p=argparse.ArgumentParser()
p.add_argument('--measure',action='store_true')
p.add_argument('--output',type=Path)
a=p.parse_args()
bundle=Path(__file__).resolve().parent
repo=bundle.parents[2]
m=json.loads((bundle/'MANIFEST.json').read_text())
for row in m['files']:
    file=repo/row['path']
    if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=row['sha256']:
        raise SystemExit('FAIL: missing/modified evidence '+row['path'])
print(f"PASS: {len(m['files'])} evidence files match SHA-256",flush=True)
if a.measure:
    if a.output is None:raise SystemExit('--measure requires an explicit --output directory')
    subprocess.run([sys.executable,str(repo/'research/vibe-core-rebuild/tools/measure_candidate.py'),
        str(bundle/'audio/hook2-raw.wav'),str(bundle/'audio/artist-target.wav'),
        str(bundle/'audio/vibe-new-core-host.wav'),str(a.output.resolve())],check=True)
