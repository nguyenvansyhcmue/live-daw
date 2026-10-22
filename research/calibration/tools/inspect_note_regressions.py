#!/usr/bin/env python3
"""Locate candidate note disagreements against a fixed-clock Artist bounce.

Offline diagnostic only.  Pitch windows are centered and hop 64 samples, so
region boundaries have approximately millisecond resolution, not sample
accuracy.  Do not use this output as a real-time detector or product policy.
"""

import argparse
import sys
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artist", type=Path)
    parser.add_argument("parent", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--pitch-tools", type=Path, required=True)
    parser.add_argument("--artist-delay", type=int, default=83)
    parser.add_argument("--vibe-delay", type=int, default=1409)
    args = parser.parse_args()
    sys.path.insert(0, str(args.pitch_tools))
    from compare_pitch_correction_bounces import pitch_track
    from measure_artist_vibe_latency_aligned import read_mono

    rate, artist_audio = read_mono(args.artist)
    parent_rate, parent_audio = read_mono(args.parent)
    candidate_rate, candidate_audio = read_mono(args.candidate)
    if parent_rate != rate or candidate_rate != rate:
        raise ValueError("sample rates differ")
    artist = pitch_track(artist_audio, rate)
    times = (artist[:, 0] - args.artist_delay) / rate
    artist_ok = np.isfinite(artist[:, 1]) & (artist[:, 2] >= 0.55)
    times = times[artist_ok]
    artist_hz = artist[artist_ok, 1]

    def resample(audio: np.ndarray) -> np.ndarray:
        track = pitch_track(audio, rate)
        ok = np.isfinite(track[:, 1]) & (track[:, 2] >= 0.55)
        return np.interp(times, (track[ok, 0] - args.vibe_delay) / rate,
                         track[ok, 1], left=np.nan, right=np.nan)

    parent_hz = resample(parent_audio)
    candidate_hz = resample(candidate_audio)
    valid = np.isfinite(parent_hz) & np.isfinite(candidate_hz) & (artist_hz > 0)
    midi = lambda hz: np.rint(69.0 + 12.0 * np.log2(np.maximum(hz, 1.0) / 440.0))
    artist_note = midi(artist_hz)
    parent_good = valid & (midi(parent_hz) == artist_note)
    candidate_good = valid & (midi(candidate_hz) == artist_note)
    gained = candidate_good & ~parent_good
    lost = parent_good & ~candidate_good
    print(f"frames={int(valid.sum())} gained={int(gained.sum())} lost={int(lost.sum())}")

    def regions(mask: np.ndarray):
        indices = np.flatnonzero(mask)
        if len(indices) == 0:
            return []
        splits = np.flatnonzero(np.diff(indices) > 1) + 1
        return np.split(indices, splits)

    for name, mask in (("lost", lost), ("gained", gained)):
        print(name)
        for section in regions(mask):
            if len(section) < 2:
                continue
            first, last = section[0], section[-1]
            print(f"{times[first]:.3f}-{times[last]:.3f}s frames={len(section)} "
                  f"Artist={int(artist_note[first])} "
                  f"parent={int(midi(parent_hz[first]))} "
                  f"candidate={int(midi(candidate_hz[first]))}")


if __name__ == "__main__":
    main()
