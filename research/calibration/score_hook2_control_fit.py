#!/usr/bin/env python3
"""Score one Vibe calibration candidate against the fixed Artist hook2 bounces.

The score deliberately compares latency-aligned pitch trajectories and event
timing, not sample waveform phase.  It is intended for bounded diagnostic
parameters only; it never writes a plug-in preset or changes production DSP.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np


def load_report(path):
    with path.open(newline="") as handle:
        return {tuple(row[name] for name in ("retune_ms", "flex_tune", "humanize", "natural_vibrato")): row
                for row in csv.DictReader(handle)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("vibe_report", type=Path)
    parser.add_argument("artist_report", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pitch-tools", type=Path, required=True)
    parser.add_argument("--retunes", nargs="+", type=float, default=[10.0, 25.0])
    parser.add_argument("--cases", nargs="*", default=None,
                        help="Exact R,F,H,V tuples, e.g. 0,25,0,0 10,25,25,0")
    args = parser.parse_args()

    sys.path.insert(0, str(args.pitch_tools))
    sys.path.insert(0, str(Path(__file__).parent))
    from fit_studioforge_transitions import event_rows
    from measure_artist_vibe_latency_aligned import envelope_delay, read_mono
    from compare_pitch_correction_bounces import pitch_track

    sample_rate, raw = read_mono(args.raw)
    vibe, artist = load_report(args.vibe_report), load_report(args.artist_report)
    requested = ([tuple(float(value) for value in item.split(",")) for item in args.cases]
                 if args.cases else [(value, 0.0, 0.0, 0.0) for value in args.retunes])
    if any(len(item) != 4 for item in requested):
        raise RuntimeError("every --cases entry must be R,F,H,V")
    rows = []
    for request in requested:
        key = tuple(f"{value:g}" for value in request)
        # CSV writers may use trailing .0; match numerically instead.
        matching = lambda source: next((row for candidate, row in source.items()
            if all(abs(float(candidate[i]) - float(key[i])) < 1e-6 for i in range(4))), None)
        vibe_row, artist_row = matching(vibe), matching(artist)
        if vibe_row is None or artist_row is None:
            raise RuntimeError(f"missing comparison bounce for {key}")
        _, a = read_mono(Path(artist_row["output"]))
        _, v = read_mono(Path(vibe_row["output"]))
        events, _, _ = event_rows(a, v, sample_rate, envelope_delay, pitch_track, raw)
        for event in events:
            event["retune_ms"], event["flex_tune"], event["humanize"], event["natural_vibrato"] = request
            rows.append(event)

    if not rows:
        raise RuntimeError("no usable pitch transitions")
    t50 = np.asarray([float(row["vibe_minus_artist_t50_ms"]) for row in rows])
    t90 = np.asarray([float(row["vibe_minus_artist_t90_ms"]) for row in rows])
    step_error = np.asarray([abs(float(row["vibe_step_cents"]) - float(row["artist_step_cents"]))
                             for row in rows])
    # Weight completion slightly higher: it reflects the audible settling of
    # a correction. Absolute terms keep a candidate from winning by being
    # early on half the events and late on the rest.
    score = float(np.median(np.abs(t50)) + 1.25 * np.median(np.abs(t90))
                  + 0.10 * np.median(step_error))
    result = {
        "events": len(rows),
        "median_abs_t50_ms": float(np.median(np.abs(t50))),
        "median_abs_t90_ms": float(np.median(np.abs(t90))),
        "median_signed_t50_ms": float(np.median(t50)),
        "median_signed_t90_ms": float(np.median(t90)),
        "median_abs_step_error_cents": float(np.median(step_error)),
        "score": score,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
