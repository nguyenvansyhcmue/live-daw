#!/usr/bin/env python3
"""Measure original-F0 vs corrected-F0 harmonic energy on one fixed WAV clock.

This narrow diagnostic is not a perceptual score: competing harmonics, formants,
and the finite FFT window can confound it. Use it only for same-input A/B tests.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile


def mono_float(path: Path):
    rate, data = wavfile.read(path)
    audio = np.asarray(data, dtype=np.float64)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if np.issubdtype(data.dtype, np.integer):
        audio /= float(np.iinfo(data.dtype).max)
    return rate, audio


def harmonic_ratio(audio, rate, centre, source_hz, target_hz, length):
    middle = int(round(centre * rate))
    frame = audio[middle - length // 2:middle + length // 2]
    if len(frame) != length:
        raise ValueError("window outside WAV")
    spectrum = np.abs(np.fft.rfft(frame * np.hanning(length)))
    freqs = np.fft.rfftfreq(length, 1.0 / rate)
    half_band = max(rate / length * 1.5, 10.0)

    def peak(hz):
        region = (freqs >= hz - half_band) & (freqs <= hz + half_band)
        return float(np.max(spectrum[region]))

    source = sum(peak(source_hz * harmonic) ** 2 for harmonic in range(4, 11))
    target = sum(peak(target_hz * harmonic) ** 2 for harmonic in range(4, 11))
    return float(10.0 * np.log10((source + 1e-20) / (target + 1e-20)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artist", type=Path, required=True)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--artist-delay", type=int, required=True)
    parser.add_argument("--parent-delay", type=int, required=True)
    parser.add_argument("--source-hz", type=float, required=True)
    parser.add_argument("--target-hz", type=float, required=True)
    parser.add_argument("--start", type=float, default=2.49)
    parser.add_argument("--end", type=float, default=2.54)
    parser.add_argument("--step", type=float, default=0.01)
    parser.add_argument("--length", type=int, default=4096)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.length <= 0 or args.length % 2:
        parser.error("length must be a positive even number")
    signals = {}
    sample_rate = None
    for label in ("artist", "parent", "candidate"):
        rate, signals[label] = mono_float(getattr(args, label))
        if sample_rate is None:
            sample_rate = rate
        elif rate != sample_rate:
            raise ValueError("sample rates differ")
    centres = np.arange(args.start, args.end + args.step * 0.5, args.step)
    rows = []
    for centre in centres:
        row = {"raw_seconds": round(float(centre), 5)}
        for label in signals:
            delay = args.artist_delay if label == "artist" else args.parent_delay
            row[label + "_source_to_target_db"] = harmonic_ratio(
                signals[label], sample_rate, centre + delay / sample_rate,
                args.source_hz, args.target_hz, args.length)
        row["candidate_minus_parent_db"] = (
            row["candidate_source_to_target_db"] - row["parent_source_to_target_db"])
        rows.append(row)
    result = {"sample_rate": sample_rate, "source_hz": args.source_hz,
              "target_hz": args.target_hz, "fft_length": args.length,
              "fixed_parent_delay_samples": args.parent_delay, "rows": rows,
              "candidate_minus_parent_median_db": float(np.median(
                  [row["candidate_minus_parent_db"] for row in rows]))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
