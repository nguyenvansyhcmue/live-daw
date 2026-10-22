#!/usr/bin/env python3
"""Compare cached, latency-aligned Hook 2 F0 traces without interpolation across gaps."""
import csv
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'artifacts'
RUNS = {
    'clean': ROOT / 'hybrid-old-render-new-policy-20261019',
    'curve': ROOT / 'hybrid-smoothstep24-20261019',
}
OUT = ROOT / 'hook2-first-two-seconds-analysis'
OUT.mkdir(exist_ok=True)


def load(path):
    with path.open(newline='') as f:
        return [dict(time=float(r['time_seconds']), midi=float(r['midi_note']),
                     confidence=float(r['confidence'])) for r in csv.DictReader(f)]


def median(xs):
    return round(statistics.median(xs), 2) if xs else ''


def nearest_legal(n):
    return min((k for k in range(math.floor(n)-4, math.floor(n)+6)
                if k % 12 in {1, 2, 4, 6, 8, 9, 11}), key=lambda k: abs(k-n))


output = []
for label, root in RUNS.items():
    traces = root / 'comparison' / 'f0-traces'
    artist = load(traces / 'case-0-artist.csv')
    vibe = load(traces / 'case-0-vibe.csv')
    # Both analyses use the same aligned sample grid. Match grid positions
    # only; do not bridge missing/unvoiced periods by interpolation.
    by_time = {round(r['time'] * 750): r for r in vibe}
    for i in range(20):
        start, end = i / 10, (i + 1) / 10
        pairs = [(a, by_time.get(round(a['time'] * 750))) for a in artist
                 if start <= a['time'] < end and a['confidence'] >= .55]
        pairs = [(a, v) for a, v in pairs if v and v['confidence'] >= .55
                 and abs(a['time'] - v['time']) < .0001]
        differences = [(v['midi'] - a['midi']) * 100 for a, v in pairs]
        output.append({
            'version': label, 'start_s': start, 'end_s': end,
            'matched_frames_confidence_ge_055': len(pairs),
            'matched_frames_confidence_ge_080': sum(a['confidence'] >= .8 and v['confidence'] >= .8 for a, v in pairs),
            'artist_median_midi': median([a['midi'] for a, _ in pairs]),
            'vibe_median_midi': median([v['midi'] for _, v in pairs]),
            'median_signed_vibe_minus_artist_cents': median(differences),
            'median_absolute_error_cents': median([abs(d) for d in differences]),
            'artist_median_nearest_scale_cents': median([abs(a['midi']-nearest_legal(a['midi']))*100 for a, _ in pairs]),
            'vibe_median_nearest_scale_cents': median([abs(v['midi']-nearest_legal(v['midi']))*100 for _, v in pairs]),
        })
with (OUT / 'f0-windows.csv').open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=output[0].keys())
    w.writeheader()
    w.writerows(output)
print(OUT / 'f0-windows.csv')
