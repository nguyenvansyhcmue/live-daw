#!/usr/bin/env python3
"""Localise aligned Artist/Vibe F0 mismatch; diagnostic only."""
import argparse
import csv
import math
from pathlib import Path

import numpy as np


def read(path):
    rows = list(csv.DictReader(open(path)))
    return np.array([(float(x['time_seconds']), float(x['f0_hz'])) for x in rows
                     if float(x['f0_hz']) > 0 and math.isfinite(float(x['f0_hz']))])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('artist'); p.add_argument('vibe'); p.add_argument('output')
    p.add_argument('--threshold-cents', type=float, default=35.0)
    p.add_argument('--gap-ms', type=float, default=24.0)
    args = p.parse_args()
    a, v = read(args.artist), read(args.vibe)
    # traces from the paired calibration analyzer already carry its latency alignment.
    # nearest neighbour rejects points farther than 4 ms instead of interpolating across unvoiced gaps.
    ai = np.searchsorted(a[:, 0], v[:, 0]); ai = np.clip(ai, 1, len(a) - 1)
    left, right = ai - 1, ai
    ix = np.where(np.abs(a[right,0]-v[:,0]) < np.abs(a[left,0]-v[:,0]), right, left)
    dt = np.abs(a[ix,0] - v[:,0])
    good = dt <= .004
    cents = 1200*np.log2(v[:,1]/a[ix,1])
    bad = good & (np.abs(cents) >= args.threshold_cents)
    segments=[]; start=None; prev=None
    for i in np.flatnonzero(bad):
        t=v[i,0]
        if start is None or t-prev > args.gap_ms/1000:
            if start is not None: segments.append((start, prev))
            start=t
        prev=t
    if start is not None: segments.append((start,prev))
    output=Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='') as f:
        w=csv.writer(f); w.writerow(['start_seconds','end_seconds','duration_ms','median_abs_cents','p90_abs_cents','matched_frames'])
        for s,e in segments:
            m=bad & (v[:,0]>=s) & (v[:,0]<=e); err=np.abs(cents[m])
            w.writerow([f'{s:.6f}',f'{e:.6f}',f'{(e-s)*1000:.3f}',f'{np.median(err):.3f}',f'{np.percentile(err,90):.3f}',int(m.sum())])
    print(f'matched={int(good.sum())} median_abs_cents={np.median(np.abs(cents[good])):.3f} segments={len(segments)} wrote={output}')

if __name__ == '__main__': main()
