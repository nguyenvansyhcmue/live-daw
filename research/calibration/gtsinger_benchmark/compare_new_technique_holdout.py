#!/usr/bin/env python3
"""Pitch A/B on new song and technique; Artist provenance remains unverified."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_gtsinger_annotation_windows import cents, read_mono, pitch_track, envelope_delay

base = Path('/Users/hiimdrdey/Library/Application Support/StudioForge/Research/GTSinger')
run = base / 'runs/artist-vibe-ab-20261017-144126'
cases = [
    ('vibrato', 'Vibrato/edelweiss/Vibrato_Group', 'Vibrato-edelweiss-0001-Vibrato_Group'),
    ('breathy', 'Breathy/all is found/Breathy_Group', 'Breathy-all_is_found-0001-Breathy_Group'),
]
for name, path, slug in cases:
    rate, raw = read_mono(base / 'English/EN-Alto-1' / path / '0001.wav')
    _, artist = read_mono(run / slug / 'artist/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav')
    delay = envelope_delay(raw, artist, rate)
    ref = pitch_track(artist, rate)
    ref = ref[np.isfinite(ref[:, 1]) & (ref[:, 2] >= .55)]
    times, hz = ref[:, 0] / rate - delay / rate, ref[:, 1]
    errors = {}
    for variant in ('baseline', 'candidate'):
        _, audio = read_mono(Path(f'/private/tmp/gtsinger-new-{name}-{variant}/full_default_render.wav'))
        offset = envelope_delay(raw, audio, rate)
        p = pitch_track(audio, rate)
        p = p[np.isfinite(p[:, 1]) & (p[:, 2] >= .55)]
        pt = p[:, 0] / rate - offset / rate
        right = np.searchsorted(pt, times)
        good = (right > 0) & (right < len(pt))
        pos = np.flatnonzero(good)
        good[pos] &= (pt[right[pos]] - pt[right[pos] - 1]) <= 64.1 / rate
        f0 = np.interp(times, pt, p[:, 1], left=np.nan, right=np.nan)
        errors[variant] = np.full(times.shape, np.nan)
        errors[variant][good] = np.abs(cents(f0[good], hz[good]))
    old, new = errors['baseline'], errors['candidate']
    good = np.isfinite(old) & np.isfinite(new)
    print(name, 'paired', good.sum(), 'baseline', np.median(old[good]), np.quantile(old[good], .9), 'candidate', np.median(new[good]), np.quantile(new[good], .9))
