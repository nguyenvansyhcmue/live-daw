#!/usr/bin/env python3
"""Narrow research diagnostic for period-to-period coherence in voiced audio.

This is not an auditory quality score.  It compares a candidate to an exact
host baseline and an external target on identical fixed windows.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile


def read(path):
    rate, data = wavfile.read(path)
    sample_dtype = data.dtype
    data = data.astype(np.float64)
    if data.ndim == 2:
        data = data.mean(axis=1)
    if np.issubdtype(sample_dtype, np.integer):
        data /= float(np.iinfo(sample_dtype).max)
    return rate, data


def coherence(x, rate, start, end):
    # The maximal 140-380 Hz autocorrelation is a robust proxy for periodic
    # grain continuity in this Alto fixture; it does not identify a cause.
    frame = round(.040 * rate)
    hop = round(.005 * rate)
    minimum = round(rate / 380)
    maximum = round(rate / 140)
    values = []
    for pos in range(round(start * rate), round(end * rate) - frame, hop):
        y = x[pos:pos + frame]
        y = (y - np.mean(y)) * np.hanning(frame)
        if np.sqrt(np.mean(y * y)) < .0003:
            continue
        scores = []
        for lag in range(minimum, maximum + 1):
            a, b = y[:-lag], y[lag:]
            scores.append(np.dot(a, b) / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-12))
        values.append(max(scores))
    return {"frames": len(values), "median": float(np.median(values)),
            "p10": float(np.quantile(values, .1))} if values else None


def main():
    parser = argparse.ArgumentParser()
    for key in ('artist', 'baseline', 'candidate'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    signals = {key: read(getattr(args, key)) for key in ('artist', 'baseline', 'candidate')}
    if len({rate for rate, _ in signals.values()}) != 1:
        raise SystemExit('sample rates differ')
    windows = ((1.2, 1.6), (2.7, 3.1), (3.3, 3.7),
               (5.4, 5.8), (8.3, 8.7), (9.2, 9.6))
    result = {str(window): {key: coherence(audio, rate, *window)
                            for key, (rate, audio) in signals.items()}
              for window in windows}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
