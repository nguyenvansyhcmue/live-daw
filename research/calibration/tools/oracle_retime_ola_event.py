#!/usr/bin/env python3
"""Offline, non-causal OLA oracle: change one event's synthesis-centre spacing.

This diagnoses whether output-centre cadence alone could explain a transition.
It is NOT a live renderer or a candidate for deployment: its OLA ledger is
collected after rendering and it changes only the traced part of a WAV.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.io import wavfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reference_wav", type=Path)
    parser.add_argument("ola_csv", type=Path)
    parser.add_argument("output_wav", type=Path)
    parser.add_argument("--event-id", type=int, required=True)
    parser.add_argument("--target-midi", type=int, required=True)
    parser.add_argument("--splice-start", type=int, required=True)
    parser.add_argument("--splice-end", type=int, required=True)
    parser.add_argument("--fade-samples", type=int, default=96)
    args = parser.parse_args()

    sample_rate, pcm = wavfile.read(args.reference_wav)
    if pcm.dtype != np.int16 or pcm.ndim != 1:
        parser.error("reference WAV must be mono PCM16")
    if not (0 <= args.splice_start < args.splice_end <= len(pcm)):
        parser.error("invalid splice region")

    rows = []
    centres = set()
    with args.ola_csv.open(newline="") as stream:
        for row in csv.DictReader(stream):
            event = int(row["targetEventId"])
            centre = int(row["synthesisMark"])
            rows.append((int(row["destinationSample"]), event, centre,
                         float(row["numeratorContribution"]),
                         float(row["weightContribution"])))
            if event == args.event_id:
                centres.add(centre)
    centres = sorted(centres)
    if len(centres) < 3:
        parser.error("trace lacks at least three grains of target event")
    target_hz = 440.0 * 2.0 ** ((args.target_midi - 69) / 12)
    target_period = sample_rate / target_hz
    moves = {centre: round(centres[0] + index * target_period) - centre
             for index, centre in enumerate(centres)}

    sums = defaultdict(float)
    weights = defaultdict(float)
    for destination, event, centre, numerator, weight in rows:
        shifted = destination + (moves[centre] if event == args.event_id else 0)
        if args.splice_start <= shifted < args.splice_end:
            sums[shifted] += numerator
            weights[shifted] += weight

    output = pcm.astype(np.float64) / 32768.0
    reconstructed = output.copy()
    missing = []
    for sample in range(args.splice_start, args.splice_end):
        if weights[sample] <= 1.0e-8:
            missing.append(sample)
        else:
            reconstructed[sample] = sums[sample] / weights[sample]
    if missing:
        parser.error(f"OLA trace misses {len(missing)} samples in splice region")
    fade = min(args.fade_samples, (args.splice_end - args.splice_start) // 2)
    gain = np.ones(args.splice_end - args.splice_start)
    if fade:
        phase = np.linspace(0.0, np.pi / 2, fade, endpoint=True)
        gain[:fade] = np.sin(phase) ** 2
        gain[-fade:] = (np.sin(phase) ** 2)[::-1]
    sl = slice(args.splice_start, args.splice_end)
    output[sl] += gain * (reconstructed[sl] - output[sl])
    wavfile.write(args.output_wav, sample_rate,
                  np.rint(np.clip(output, -1.0, 32767.0 / 32768.0) * 32768).astype(np.int16))
    print("target_period_samples", round(target_period, 3))
    print("grain_centres_and_moves", [(centre, moves[centre]) for centre in centres])
    print("oracle_not_realtime_or_deployable", args.output_wav)


if __name__ == "__main__":
    main()
