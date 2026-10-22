#!/usr/bin/env python3
"""Compare globally level-matched, latency-aligned vocal envelopes.

Delays are measured externally against the same raw recording. Windows are
on that raw timeline; they are not sample-accurate phoneme annotations.
"""
import argparse
import csv
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile


def read_audio(path):
    rate, data = wavfile.read(path)
    if np.issubdtype(data.dtype, np.integer):
        data = data.astype(np.float64) / max(abs(np.iinfo(data.dtype).min), np.iinfo(data.dtype).max)
    else:
        data = data.astype(np.float64)
    return rate, data.mean(axis=1) if data.ndim == 2 else data


def rms(data):
    return float(np.sqrt(np.mean(data * data))) if len(data) else float('nan')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artist', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--delays', nargs=3, type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    values = [read_audio(path) for path in (args.artist, args.baseline, args.candidate)]
    rate = values[0][0]
    if any(r != rate for r, _ in values) or any(d < 0 for d in args.delays):
        raise ValueError('Sample rates must match and delays must be nonnegative')
    signals = [v[d:] for (_, v), d in zip(values, args.delays)]
    length = min(map(len, signals))
    signals = [s[:length] for s in signals]
    # One global gain per render; never normalize individual windows.
    reference_rms = rms(signals[0])
    gains = [1.0] + [reference_rms / rms(s) for s in signals[1:]]
    signals = [s * gain for s, gain in zip(signals, gains)]
    sos = signal.butter(4, 5000, btype='highpass', fs=rate, output='sos')
    high = [signal.sosfilt(sos, s) for s in signals]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['start_s', 'end_s', 'band', 'artist_rms', 'baseline_rms',
                         'candidate_rms', 'baseline_vs_artist_db', 'candidate_vs_artist_db'])
        for start in np.arange(4.14, 4.40, 0.02):
            lo, hi = round(start * rate), round((start + 0.02) * rate)
            if hi > length:
                break
            for band, group in [('full', signals), ('above_5khz', high)]:
                levels = [rms(x[lo:hi]) for x in group]
                delta = [20 * np.log10(max(x, 1e-12) / max(levels[0], 1e-12)) for x in levels[1:]]
                writer.writerow([f'{start:.3f}', f'{start + 0.02:.3f}', band,
                                 *[f'{x:.8f}' for x in levels], *[f'{x:.3f}' for x in delta]])
    print('sample_rate=', rate, 'global_gains=', gains, 'output=', args.output)


if __name__ == '__main__':
    main()
