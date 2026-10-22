#!/usr/bin/env python3
"""Compare smoothed spectral envelopes, without treating them as formant proof."""
import argparse
import csv
from pathlib import Path

import numpy as np
from scipy import ndimage, signal
from diagnose_vocal_texture_ab import delay_against, read_mono, trim_delay


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--artist', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    sr, raw = read_mono(args.raw)
    ar, artist = read_mono(args.artist)
    cr, candidate = read_mono(args.candidate)
    if sr != ar or sr != cr:
        raise SystemExit('sample rate mismatch')
    da, dc = delay_against(raw, artist, sr), delay_against(raw, candidate, sr)
    length = min(len(raw), len(artist) - max(da, 0), len(candidate) - max(dc, 0))
    artist, candidate = trim_delay(artist, da, length), trim_delay(candidate, dc, length)
    artist /= max(np.sqrt(np.mean(artist ** 2)), 1e-12)
    candidate /= max(np.sqrt(np.mean(candidate ** 2)), 1e-12)
    f, t, a = signal.stft(artist, fs=sr, nperseg=2048, noverlap=1536, boundary=None)
    _, _, b = signal.stft(candidate, fs=sr, nperseg=2048, noverlap=1536, boundary=None)
    # Smooth over approximately 200 Hz to suppress individual harmonics.
    a_db = ndimage.gaussian_filter1d(20*np.log10(np.maximum(np.abs(a), 1e-8)), 200/(sr/2048), axis=0)
    b_db = ndimage.gaussian_filter1d(20*np.log10(np.maximum(np.abs(b), 1e-8)), 200/(sr/2048), axis=0)
    energy = np.sqrt(np.mean(np.abs(a)**2, axis=0))
    rows = []
    for second in range(int(t[-1])+1):
        use = (t >= second) & (t < second+1) & (energy > np.max(energy)*0.04)
        if np.count_nonzero(use) < 5:
            continue
        row = [second, int(np.count_nonzero(use))]
        for low, high in ((200, 800), (800, 2000), (2000, 4000), (4000, 8000)):
            bins = (f >= low) & (f < high)
            row.append(float(np.median((b_db-a_db)[bins][:, use])))
        rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='') as out:
        writer = csv.writer(out)
        writer.writerow(['second', 'active_frames', 'delta_200_800_db', 'delta_800_2000_db',
                         'delta_2000_4000_db', 'delta_4000_8000_db'])
        writer.writerows(rows)
    print(f'artist_delay={da} candidate_delay={dc} windows={len(rows)} output={args.output}')


if __name__ == '__main__':
    main()
