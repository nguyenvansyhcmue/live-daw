#!/usr/bin/env python3
"""Compare experimental detector renders to historical Artist bounces.

Diagnostic only: the historical reference lacks binary-hash and parameter
readback provenance. Pitch confidence gaps are never interpolated across.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_gtsinger_annotation_windows import tagged_intervals, in_intervals, cents, pitch_track, read_mono, envelope_delay

base = Path('/Users/hiimdrdey/Library/Application Support/StudioForge/Research/GTSinger')
data = base / 'English/EN-Alto-1/Glissando/for the first time in forever/Glissando_Group'
run = base / 'runs/artist-vibe-ab-20261017-144126'
for clip in ('0001', '0002'):
    raw_path = data / (clip + '.wav')
    artist_path = run / f'Glissando-for_the_first_time_in_forever-{clip}-Glissando_Group/artist/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav'
    rate, raw = read_mono(raw_path)
    _, artist = read_mono(artist_path)
    artist_delay = envelope_delay(raw, artist, rate)
    a = pitch_track(artist, rate)
    valid = np.isfinite(a[:, 1]) & (a[:, 2] >= .55)
    times = a[valid, 0] / rate - artist_delay / rate
    ahz = a[valid, 1]
    tagged = in_intervals(times, tagged_intervals(raw_path.with_suffix('.json'), 'glissando'))
    variant_errors = {}
    for variant in ('threshold', 'floorguard', 'periodicguard'):
        _, audio = read_mono(Path('/private/tmp') / f'gtsinger-{variant}-{clip}/full_default_render.wav')
        delay = envelope_delay(raw, audio, rate)
        v = pitch_track(audio, rate)
        v = v[np.isfinite(v[:, 1]) & (v[:, 2] >= .55)]
        vt = v[:, 0] / rate - delay / rate
        right = np.searchsorted(vt, times)
        inside = (right > 0) & (right < len(vt))
        positions = np.flatnonzero(inside)
        good = np.zeros(len(times), dtype=bool)
        good[positions] = (vt[right[positions]] - vt[right[positions]-1]) <= 64.1 / rate
        values = np.interp(times, vt, v[:, 1], left=np.nan, right=np.nan)
        good &= np.isfinite(values) & tagged
        error = np.abs(cents(values[good], ahz[good]))
        all_error = np.full(times.shape, np.nan)
        all_error[good] = error
        variant_errors[variant] = all_error
        print(f'{clip} {variant} frames={len(error)} median={np.median(error):.3f} p90={np.quantile(error,.9):.3f} artist_delay={artist_delay} vibe_delay={delay}')
    for variant in ('floorguard', 'periodicguard'):
        old, new = variant_errors['threshold'], variant_errors[variant]
        paired = np.isfinite(old) & np.isfinite(new)
        print(f'{clip} {variant} paired={paired.sum()} baseline_median={np.median(old[paired]):.3f} candidate_median={np.median(new[paired]):.3f} baseline_p90={np.quantile(old[paired],.9):.3f} candidate_p90={np.quantile(new[paired],.9):.3f}')
        buckets = []
        for start in np.arange(0, max(times), .25):
            mask = paired & (times >= start) & (times < start + .25)
            if mask.sum() >= 20:
                buckets.append((float(np.median(new[mask])-np.median(old[mask])), float(start), int(mask.sum()), float(np.median(old[mask])), float(np.median(new[mask]))))
        print(f'{clip} {variant} worst_250ms_change=', sorted(buckets, reverse=True)[:4])
