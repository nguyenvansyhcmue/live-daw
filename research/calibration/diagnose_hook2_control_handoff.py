#!/usr/bin/env python3
"""Attribute fitted audio transition timing to selector, control, or OLA handoff.

This is forensic-only: it reads an existing SignalChainDiagnostic CSV and
never changes the plugin or its state.
"""
import argparse
import csv
from pathlib import Path


def as_int(row, key):
    try:
        return int(float(row[key]))
    except (KeyError, ValueError):
        return -1


def first_change(rows, start, before, key):
    prior = before
    for row in rows:
        value = as_int(row, key)
        if value >= 0 and value != prior:
            return float(row["timeMs"]) / 1000.0, value
    return None, -1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument("events", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--radius-ms", type=float, default=220.0)
    args = parser.parse_args()
    radius = args.radius_ms / 1000.0

    with args.trace.open(newline="") as handle:
        trace = list(csv.DictReader(handle))
    with args.events.open(newline="") as handle:
        events = list(csv.DictReader(handle))

    keys = ["committedTargetMidi", "sourceControlTargetMidi", "outputRendererControlTargetMidi", "olaDominantGrainTargetMidi"]
    report = [
        "# Hook-2 selector → control → OLA handoff diagnosis",
        "",
        "Offsets are relative to the fitted Artist event. A positive value means Vibe's stage changed later. "
        "This is only provenance; it does not alter DSP.",
        "",
        "| Artist event | Audio t50 Δ | Selector commit | Source control | Output control | Audible OLA grain |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for event in events:
        time = float(event["time_seconds"])
        window = [r for r in trace if time - radius <= float(r["timeMs"]) / 1000.0 <= time + radius]
        before_rows = [r for r in trace if float(r["timeMs"]) / 1000.0 < time - .002]
        if not window or not before_rows:
            continue
        values = []
        for key in keys:
            baseline = as_int(before_rows[-1], key)
            changed_time, changed_value = first_change(window, time, baseline, key)
            values.append("—" if changed_time is None else f"{(changed_time - time) * 1000.0:+.1f} ms → {changed_value}")
        report.append(
            f"| {time:.3f}s {event['direction']} | {float(event['vibe_minus_artist_t50_ms']):+.1f} ms | "
            + " | ".join(values) + " |"
        )
    report.extend([
        "",
        "## Reading the result",
        "",
        "- Selector late, with all later columns following it: detector/target policy is the cause.",
        "- Selector and source control timely, output/OLA late: renderer control or OLA handoff is the cause.",
        "- OLA changes on time but audio t50 remains late: synthesis contour/window is the cause.",
        "",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(report))
    print(args.output)


if __name__ == "__main__":
    main()
