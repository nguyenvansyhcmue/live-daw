#!/usr/bin/env python3
"""Audit which rendered grains own a measured raw-clock note transition.

This is an offline diagnostic. It never changes DSP or infers a plug-in's
private control law from the target WAV. All times are mapped through one
explicit, fixed render latency rather than independently realigned per case.
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ola_csv", type=Path)
    parser.add_argument("--latency-samples", type=int, required=True)
    parser.add_argument("--sample-rate", type=int, default=48000)
    parser.add_argument("--raw-t10-ms", type=float, required=True)
    parser.add_argument("--raw-t50-ms", type=float, required=True)
    parser.add_argument("--raw-t90-ms", type=float, required=True)
    parser.add_argument("--radius-samples", type=int, default=16)
    args = parser.parse_args()

    contributions = defaultdict(list)
    grains = {}
    with args.ola_csv.open(newline="") as stream:
        for row in csv.DictReader(stream):
            destination = int(row["destinationSample"])
            grain_id = int(row["grainId"])
            event_id = int(row["targetEventId"])
            weight = float(row["weightContribution"])
            contributions[destination].append((event_id, weight))
            grains[(grain_id, event_id)] = {
                "synthesis_mark": grain_id,
                "target_event": event_id,
                "target_midi": int(row["targetMidi"]),
                "source_mark": int(row["sourceMark"]),
                "half_window": int(row["halfWindow"]),
                "ratio_metadata": float(row["ratio"]),
            }

    points = {}
    for label, raw_ms in (("t10", args.raw_t10_ms), ("t50", args.raw_t50_ms),
                          ("t90", args.raw_t90_ms)):
        output_sample = round(raw_ms * args.sample_rate / 1000 + args.latency_samples)
        by_event = defaultdict(float)
        for destination in range(output_sample - args.radius_samples,
                                 output_sample + args.radius_samples + 1):
            for event_id, weight in contributions[destination]:
                by_event[event_id] += weight
        total = sum(by_event.values())
        if total <= 0.0:
            parser.error(f"OLA trace does not cover {label} at output sample {output_sample}")
        points[label] = {
            "raw_ms": raw_ms,
            "output_sample": output_sample,
            "event_weight_fraction": {
                str(event_id): round(weight / total, 6)
                for event_id, weight in sorted(by_event.items())
            },
        }

    low = points["t10"]["output_sample"] - args.radius_samples
    high = points["t90"]["output_sample"] + args.radius_samples
    relevant_grains = sorted(
        (grain for grain in grains.values()
         if grain["synthesis_mark"] + grain["half_window"] >= low
         and grain["synthesis_mark"] - grain["half_window"] <= high),
        key=lambda grain: grain["synthesis_mark"],
    )
    print(json.dumps({"points": points, "grains": relevant_grains}, indent=2))


if __name__ == "__main__":
    main()
