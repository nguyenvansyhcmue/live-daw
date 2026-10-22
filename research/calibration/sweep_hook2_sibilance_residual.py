#!/usr/bin/env python3
"""Offline-only residual high-band sweep against the frozen Artist bounce.

This emulates the TD-PSOLA dry-high/wet-high crossover at fixed candidate
latency.  It never loads, edits, or installs a plug-in.  Its purpose is to
bound a safe residual mix before changing the real-time detector.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile


def read_mono(path: Path) -> tuple[int, np.ndarray]:
    rate, data = wavfile.read(path)
    if np.issubdtype(data.dtype, np.integer):
        data = data.astype(np.float64) / np.iinfo(data.dtype).max
    else:
        data = data.astype(np.float64)
    return rate, data.mean(axis=1) if data.ndim == 2 else data


def lowpass(signal: np.ndarray, rate: int, cutoff: float = 2800.0) -> np.ndarray:
    alpha = 1.0 - np.exp(-2.0 * np.pi * cutoff / rate)
    out = np.empty_like(signal)
    state = 0.0
    for index, sample in enumerate(signal):
        state += (sample - state) * alpha
        out[index] = state
    return out


def band_ratio(signal: np.ndarray, rate: int) -> tuple[float, float]:
    if len(signal) < 64:
        return 0.0, 0.0
    spectrum = np.abs(np.fft.rfft(signal * np.hanning(len(signal)))) ** 2
    frequencies = np.fft.rfftfreq(len(signal), 1.0 / rate)
    vocal = spectrum[(frequencies >= 250.0) & (frequencies < 4000.0)].sum()
    high = spectrum[(frequencies >= 4000.0) & (frequencies < min(12000.0, rate * 0.5))].sum()
    return float(high / max(vocal + high, 1e-18)), float(np.sqrt(np.mean(signal * signal)))


def window(signal: np.ndarray, centre: int, half: int) -> np.ndarray:
    return signal[max(0, centre - half): min(len(signal), centre + half)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("artist", type=Path)
    parser.add_argument("vibe", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pitch-tools", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=10)
    args = parser.parse_args()
    sys.path.insert(0, str(args.pitch_tools))
    from measure_artist_vibe_latency_aligned import envelope_delay

    rate, raw = read_mono(args.raw)
    artist_rate, artist = read_mono(args.artist)
    vibe_rate, vibe = read_mono(args.vibe)
    if rate != artist_rate or rate != vibe_rate:
        raise SystemExit("sample-rate mismatch")
    artist_delay = envelope_delay(raw, artist, rate)
    vibe_delay = envelope_delay(raw, vibe, rate)
    raw_delayed = np.pad(raw, (vibe_delay, 0))[:len(vibe)]
    vibe_low, raw_low = lowpass(vibe, rate), lowpass(raw_delayed, rate)
    vibe_high, raw_high = vibe - vibe_low, raw_delayed - raw_low

    half, hop = int(0.010 * rate), int(0.005 * rate)
    candidates = []
    for centre in range(half, len(raw) - half, hop):
        ratio, rms = band_ratio(window(raw, centre, half), rate)
        if rms > 0.0025:
            candidates.append((ratio, centre))
    candidates.sort(reverse=True)
    centres: list[int] = []
    for _, centre in candidates:
        if all(abs(centre - prior) >= int(0.030 * rate) for prior in centres):
            centres.append(centre)
        if len(centres) >= 30:
            break

    rows = []
    for step in range(args.steps + 1):
        amount = step / args.steps
        hybrid = vibe_low + (1.0 - amount) * vibe_high + amount * raw_high
        high_errors, gain_errors = [], []
        for centre in centres:
            artist_ratio, artist_rms = band_ratio(window(artist, centre + artist_delay, half), rate)
            hybrid_ratio, hybrid_rms = band_ratio(window(hybrid, centre + vibe_delay, half), rate)
            high_errors.append(abs(hybrid_ratio - artist_ratio))
            gain_errors.append(abs(20.0 * np.log10(max(hybrid_rms, 1e-12) / max(artist_rms, 1e-12))))
        rows.append({
            "residual_mix": amount,
            "median_abs_high_fraction_error": float(np.median(high_errors)),
            "p90_abs_high_fraction_error": float(np.percentile(high_errors, 90)),
            "median_abs_gain_error_db": float(np.median(gain_errors)),
            "p90_abs_gain_error_db": float(np.percentile(gain_errors, 90)),
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)
    best = min(rows, key=lambda row: (row["median_abs_high_fraction_error"], row["p90_abs_high_fraction_error"]))
    print(f"artist_delay_samples={artist_delay}")
    print(f"vibe_delay_samples={vibe_delay}")
    print(f"best_residual_mix={best['residual_mix']:.3f}")
    print(args.output)


if __name__ == "__main__":
    main()
