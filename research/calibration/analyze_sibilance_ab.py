#!/usr/bin/env python3
"""Measure candidate sibilant regions in identical Artist/Vibe bounces.

This is an analysis-only black-box tool. It finds energetic high-frequency,
noise-like regions in the raw vocal, then measures the corresponding aligned
region in both renders. It does not alter a DAW session or plug-in state.
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile


def read_mono(path: Path):
    rate, data = wavfile.read(path)
    if np.issubdtype(data.dtype, np.integer):
        data = data.astype(np.float64) / np.iinfo(data.dtype).max
    else:
        data = data.astype(np.float64)
    if data.ndim == 2:
        data = data.mean(axis=1)
    return rate, data


def band_ratio(x, rate):
    """Return high/(vocal+high) energy and rms for a short time window."""
    if len(x) < 64:
        return 0.0, 0.0
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freq = np.fft.rfftfreq(len(x), 1.0 / rate)
    vocal = spectrum[(freq >= 250.0) & (freq < 4000.0)].sum()
    high = spectrum[(freq >= 4000.0) & (freq < min(12000.0, rate * 0.5))].sum()
    return float(high / max(vocal + high, 1e-18)), float(np.sqrt(np.mean(x * x)))


def rms_db(value):
    return 20.0 * np.log10(max(value, 1e-12))


def extract(signal, centre, half):
    begin = max(0, centre - half)
    end = min(len(signal), centre + half)
    return signal[begin:end]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("artist", type=Path)
    parser.add_argument("vibe", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pitch-tools", type=Path, required=True)
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()
    sys.path.insert(0, str(args.pitch_tools))
    from measure_artist_vibe_latency_aligned import envelope_delay

    rate, raw = read_mono(args.raw)
    artist_rate, artist = read_mono(args.artist)
    vibe_rate, vibe = read_mono(args.vibe)
    if artist_rate != rate or vibe_rate != rate:
        raise RuntimeError("sample-rate mismatch")
    artist_delay = envelope_delay(raw, artist, rate)
    vibe_delay = envelope_delay(raw, vibe, rate)

    # 20 ms analysis windows, inspected each 5 ms. A 30-ms NMS radius keeps
    # a sustained /s/ from appearing as many independent candidates.
    half = max(1, int(0.010 * rate))
    hop = max(1, int(0.005 * rate))
    candidates = []
    for centre in range(half, len(raw) - half, hop):
        ratio, rms = band_ratio(extract(raw, centre, half), rate)
        if rms > 0.0025:
            candidates.append((ratio, rms, centre))
    candidates.sort(reverse=True)
    selected = []
    for ratio, rms, centre in candidates:
        if all(abs(centre - prior[2]) >= int(0.030 * rate) for prior in selected):
            selected.append((ratio, rms, centre))
        if len(selected) >= args.top:
            break
    selected.sort(key=lambda x: x[2])

    rows = []
    for raw_ratio, raw_rms, centre in selected:
        artist_ratio, artist_rms = band_ratio(extract(artist, centre + artist_delay, half), rate)
        vibe_ratio, vibe_rms = band_ratio(extract(vibe, centre + vibe_delay, half), rate)
        rows.append({
            "raw_time_seconds": round(centre / rate, 6),
            "raw_high_fraction": raw_ratio,
            "artist_high_fraction": artist_ratio,
            "vibe_high_fraction": vibe_ratio,
            "vibe_minus_artist_high_fraction": vibe_ratio - artist_ratio,
            "artist_rms_db": rms_db(artist_rms),
            "vibe_rms_db": rms_db(vibe_rms),
            "vibe_minus_artist_rms_db": rms_db(vibe_rms) - rms_db(artist_rms),
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys() if rows else ["raw_time_seconds"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"artist_delay_samples={artist_delay}")
    print(f"vibe_delay_samples={vibe_delay}")
    print(f"regions={len(rows)}")
    print(args.output)


if __name__ == "__main__":
    main()
