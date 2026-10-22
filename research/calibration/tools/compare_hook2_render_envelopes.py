#!/usr/bin/env python3
"""Compare raw-aligned vocal dynamics and broad spectral colour.

This intentionally does not compare phase or claim perceptual equivalence.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import stft


def frames(signal, size, hop):
    count = 1 + (len(signal) - size) // hop
    return np.lib.stride_tricks.sliding_window_view(signal, size)[::hop][:count]


def measure(raw, artist, candidate, rate, artist_delay, candidate_delay):
    end = min(len(raw), len(artist) - artist_delay, len(candidate) - candidate_delay)
    source = raw[:end]
    target = artist[artist_delay:artist_delay + end]
    test = candidate[candidate_delay:candidate_delay + end]
    size, hop = int(0.040 * rate), int(0.010 * rate)
    a, b, r = (frames(x, size, hop) for x in (target, test, source))
    rms = lambda x: np.sqrt(np.mean(x * x, axis=1) + 1e-15)
    ar, br, rr = rms(a), rms(b), rms(r)
    frame_time = (np.arange(len(ar)) * hop + size / 2) / rate
    active = (frame_time >= 0.2) & (frame_time <= 10.5) & (ar > 10 ** (-45 / 20)) & (rr > 10 ** (-50 / 20))
    level_delta = 20 * np.log10(br[active] / ar[active])
    # Broad bands, not phase-sensitive FFT-bin matching. For each active frame,
    # remove its overall RMS before comparing the spectrum.
    taper = np.hanning(size)
    fa = np.abs(np.fft.rfft(a[active] * taper, axis=1)) ** 2
    fb = np.abs(np.fft.rfft(b[active] * taper, axis=1)) ** 2
    frequencies = np.fft.rfftfreq(size, 1 / rate)
    bands = ((100, 300), (300, 700), (700, 1500), (1500, 3000), (3000, 6000), (6000, 10000))
    colour = {}
    for lo, hi in bands:
        select = (frequencies >= lo) & (frequencies < hi)
        ap = fa[:, select].sum(axis=1) / np.maximum(fa.sum(axis=1), 1e-15)
        bp = fb[:, select].sum(axis=1) / np.maximum(fb.sum(axis=1), 1e-15)
        delta = 10 * np.log10(np.maximum(bp, 1e-15) / np.maximum(ap, 1e-15))
        colour[f"{lo}-{hi}_hz_median_db"] = float(np.median(delta))
    median_level = float(np.median(level_delta))
    return {
        "active_frames": int(active.sum()),
        "median_level_delta_db": median_level,
        "p90_absolute_level_delta_db": float(np.quantile(np.abs(level_delta), .90)),
        "p90_level_shape_error_after_gain_match_db": float(np.quantile(np.abs(level_delta - median_level), .90)),
        "rms_envelope_correlation": float(np.corrcoef(ar[active], br[active])[0, 1]),
        "artist_delay_samples": artist_delay,
        "candidate_delay_samples": candidate_delay,
        "spectral_band_delta_db": colour,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("artist", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--candidate", action="append", nargs=2, metavar=("NAME", "WAV"), required=True)
    parser.add_argument("--pitch-tools", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.pitch_tools))
    from measure_artist_vibe_latency_aligned import envelope_delay, read_mono

    rate, raw = read_mono(args.raw)
    arate, artist = read_mono(args.artist)
    if rate != arate:
        raise RuntimeError("Artist sample rate differs from raw")
    artist_delay = envelope_delay(raw, artist, rate)
    results = {}
    for name, path in args.candidate:
        vrate, vibe = read_mono(Path(path))
        if vrate != rate:
            raise RuntimeError(f"sample rate differs: {path}")
        delay = envelope_delay(raw, vibe, rate)
        results[name] = measure(raw, artist, vibe, rate, artist_delay, delay)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
