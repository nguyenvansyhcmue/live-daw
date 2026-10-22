#!/usr/bin/env python3
"""Separate tracker, selector and audible pitch at newly accepted frames."""
import csv
import sys
from collections import Counter
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_gtsinger_annotation_windows import read_mono, pitch_track, envelope_delay, tagged_intervals, in_intervals

base = Path('/Users/hiimdrdey/Library/Application Support/StudioForge/Research/GTSinger')
data = base / 'English/EN-Alto-1/Glissando/for the first time in forever/Glissando_Group'
run = base / 'runs/artist-vibe-ab-20261017-144126'

def frames(path):
    with path.open(newline='') as f:
        rows = csv.DictReader(f)
        return {int(r['detectorFrameEnd']): r for r in rows if int(r['detectorFrameEnd']) > 1024}

def track(path, raw, rate):
    sr, audio = read_mono(path)
    if sr != rate:
        raise ValueError('sample rate mismatch')
    delay = envelope_delay(raw, audio, rate)
    p = pitch_track(audio, rate)
    good = np.isfinite(p[:,1]) & (p[:,2] >= .55)
    return p[good, 0] / rate - delay / rate, p[good, 1]

def nearby(times, values, target):
    i = np.searchsorted(times, target)
    if i == 0 or i >= len(times) or times[i] - times[i-1] > 64.1 / 48000:
        return np.nan
    return np.interp(target, times[i-1:i+1], values[i-1:i+1])

for clip in ('0001', '0002'):
    raw_path = data / (clip + '.wav')
    rate, raw = read_mono(raw_path)
    artist = run / f'Glissando-for_the_first_time_in_forever-{clip}-Glissando_Group/artist/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav'
    at, af = track(artist, raw, rate)
    before = frames(Path(f'/private/tmp/gtsinger-threshold-{clip}/full_default_intervals.csv'))
    after = frames(Path(f'/private/tmp/gtsinger-floorguard-{clip}/full_default_intervals.csv'))
    vt, vf = track(Path(f'/private/tmp/gtsinger-floorguard-{clip}/full_default_render.wav'), raw, rate)
    intervals = tagged_intervals(raw_path.with_suffix('.json'), 'glissando')
    result = Counter()
    diffs = []
    for end in sorted(before.keys() & after.keys()):
        old, new = before[end], after[end]
        if int(old['detectorRejectMask']) == 0 or int(new['detectorRejectMask']) != 0:
            continue
        # Frame-centre association is approximate: detector and renderer
        # clocks differ and the analysis window spans 21.3 ms.
        t = (end - 512) / rate
        if not in_intervals(np.array([t]), intervals)[0]:
            continue
        ref = nearby(at, af, t)
        output = nearby(vt, vf, t)
        if not (np.isfinite(ref) and np.isfinite(output)):
            continue
        target = int(new['committedTargetMidi'])
        artist_note = round(69 + 12 * np.log2(ref / 440.0))
        if target < 0:
            result['no_target'] += 1
            continue
        result['target_matches_artist_note' if target == artist_note else 'target_differs_artist_note'] += 1
        error = abs(1200 * np.log2(output / ref))
        result['output_error_gt_50ct' if error > 50 else 'output_error_le_50ct'] += 1
        diffs.append(error)
    print(clip, dict(result), 'median_output_error', round(float(np.median(diffs)),2) if diffs else None, 'frames',len(diffs))
