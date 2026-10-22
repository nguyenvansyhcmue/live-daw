#!/usr/bin/env python3
"""Paired pitch-valid holdout comparison; historical Artist provenance is incomplete."""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_gtsinger_annotation_windows import cents, read_mono, pitch_track, envelope_delay

base = Path('/Users/hiimdrdey/Library/Application Support/StudioForge/Research/GTSinger')
data = base / 'English/EN-Alto-1/Glissando/for the first time in forever/Control_Group'
run = base / 'runs/artist-vibe-ab-20261017-144126'
for clip in ('0001', '0002'):
    rate, raw = read_mono(data / (clip + '.wav'))
    ref_path = run / f'Glissando-for_the_first_time_in_forever-{clip}-Control_Group/artist/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav'
    _, ref = read_mono(ref_path)
    delay = envelope_delay(raw, ref, rate)
    p = pitch_track(ref, rate)
    p = p[np.isfinite(p[:, 1]) & (p[:, 2] >= .55)]
    times, reference = p[:, 0] / rate - delay / rate, p[:, 1]
    errors = {}
    for name in ('baseline', 'candidate'):
        _, audio = read_mono(Path(f'/private/tmp/gtsinger-holdout-{name}-{clip}/full_default_render.wav'))
        offset = envelope_delay(raw, audio, rate)
        q = pitch_track(audio, rate)
        q = q[np.isfinite(q[:, 1]) & (q[:, 2] >= .55)]
        qt = q[:, 0] / rate - offset / rate
        right = np.searchsorted(qt, times)
        valid = (right > 0) & (right < len(qt))
        i = np.flatnonzero(valid)
        valid[i] &= (qt[right[i]] - qt[right[i]-1]) <= 64.1 / rate
        hz = np.interp(times, qt, q[:, 1], left=np.nan, right=np.nan)
        e = np.full(times.shape, np.nan)
        e[valid] = np.abs(cents(hz[valid], reference[valid]))
        errors[name] = e
    old, new = errors['baseline'], errors['candidate']
    paired = np.isfinite(old) & np.isfinite(new)
    print(clip, 'paired', paired.sum(), 'baseline', np.median(old[paired]), np.quantile(old[paired], .9), 'candidate', np.median(new[paired]), np.quantile(new[paired], .9))
