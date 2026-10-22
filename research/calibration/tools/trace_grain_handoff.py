#!/usr/bin/env python3
"""Report one note handoff from an existing Vibe interval trace.

All reported indices are from the diagnostic render's own sample clock.  This
tool deliberately does not align an independently hosted WAV or infer the
physical onset of a sung pitch change.
"""

import argparse
import csv
import math
from pathlib import Path


def number(row, key):
    try:
        return float(row[key])
    except (KeyError, ValueError):
        return math.nan


def sample(row):
    return int(row["sampleIndex"])


def print_milestone(name, row, rate, detail=""):
    if row is None:
        print(f"{name}: not observed")
        return
    index = sample(row)
    print(f"{name}: sample={index} time_ms={index * 1000 / rate:.3f} {detail}".rstrip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intervals", type=Path)
    parser.add_argument("--near-seconds", type=float, default=8.356)
    parser.add_argument("--sample-rate", type=int, default=48000)
    parser.add_argument("--search-ms", type=float, default=100.0)
    args = parser.parse_args()

    center = round(args.near_seconds * args.sample_rate)
    radius = round(args.search_ms * args.sample_rate / 1000)
    with args.intervals.open(newline="") as stream:
        rows = [row for row in csv.DictReader(stream)
                if abs(sample(row) - center) <= radius]
    changes = [row for row in rows if row.get("targetChanged") == "1"]
    if not changes:
        raise SystemExit("No target commit in the requested window")
    commit = min(changes, key=lambda row: abs(sample(row) - center))
    old_rows = [row for row in rows if sample(row) < sample(commit)]
    if not old_rows:
        raise SystemExit("Trace window does not contain the previous target")
    old_note = int(old_rows[-1]["committedTargetMidi"])
    new_note = int(commit["committedTargetMidi"])
    midpoint_hz = 440 * 2 ** (((old_note + new_note) / 2 - 69) / 12)
    before = [row for row in rows if sample(row) <= sample(commit)]
    if new_note < old_note:
        crossed = [row for row in before if number(row, "rawF0") <= midpoint_hz]
    else:
        crossed = [row for row in before if number(row, "rawF0") >= midpoint_hz]
    midpoint = crossed[0] if crossed else None

    after = [row for row in rows if sample(row) >= sample(commit)]
    spawned = next((row for row in after
                    if int(row.get("spawnTargetMidi") or -1) == new_note), None)
    dominant = next((row for row in after
                     if int(row.get("olaDominantGrainTargetMidi") or -1) == new_note), None)

    print(f"clock=diagnostic_input_sample rate={args.sample_rate}Hz "
          f"old_target={old_note} new_target={new_note} midpoint_hz={midpoint_hz:.3f}")
    print_milestone("raw_F0_crosses_note_midpoint", midpoint, args.sample_rate,
                    f"raw_F0_hz={number(midpoint, 'rawF0'):.3f}" if midpoint else "")
    print_milestone("selector_commit_observed", commit, args.sample_rate)
    print_milestone("new_target_grain_spawn_observed", spawned, args.sample_rate)
    print_milestone("new_target_grain_dominant_observed", dominant, args.sample_rate)
    if midpoint:
        print(f"midpoint_to_commit_samples={sample(commit) - sample(midpoint)}")
    if spawned:
        print(f"commit_to_spawn_samples={sample(spawned) - sample(commit)}")
    if dominant:
        print(f"commit_to_dominant_samples={sample(dominant) - sample(commit)}")
    print("warning=These are sampled diagnostic observations, not physical T0, "
          "first audible grain, or a DAW-host/Artist output alignment.")


if __name__ == "__main__":
    main()
