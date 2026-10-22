#!/usr/bin/env python3
"""Summarise target-event to renderer-control publication from Vibe diagnostics.

This is read-only analysis. It deliberately does not infer audible timing from
waveform pitch: it measures the timestamp ownership hand-off already exported
by the processor, so scheduler delay can be distinguished from detector delay.
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path


def percentile(values: list[float], amount: float) -> float:
    if not values:
        return float("nan")
    values = sorted(values)
    position = (len(values) - 1) * amount
    lower, upper = int(position), min(int(position) + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: analyze_renderer_control_materialization.py <diagnostic-case-dir>")
    case = Path(sys.argv[1])
    source = case / "control_materialization_events.csv"
    if not source.exists():
        raise SystemExit(f"missing trace: {source}")

    first_publication: dict[int, dict[str, float]] = {}
    with source.open(newline="") as handle:
        for raw in csv.DictReader(handle):
            try:
                event = int(raw["targetEventId"])
                published = int(raw["publishedToPsolaRing"]) != 0
                delay = float(raw["publicationDelaySamples"])
                timestamp = float(raw["timestampSamples"])
                scheduled = float(raw["scheduledCorrectionCents"])
            except (KeyError, ValueError):
                continue
            if event < 0 or not published or event in first_publication:
                continue
            first_publication[event] = {"delay": delay, "timestamp": timestamp, "scheduled": scheduled}

    rows = [first_publication[key] | {"event": key} for key in sorted(first_publication)]
    delays = [row["delay"] for row in rows]
    report = case / "renderer-control-materialization-summary.md"
    with report.open("w") as out:
        out.write("# Target event → renderer-control materialization\n\n")
        out.write("This measures only internal scheduler publication. It is not output latency or pitch-detection latency.\n\n")
        out.write(f"- Target events with a first ring publication: {len(rows)}\n")
        if delays:
            out.write(f"- Median publication delay: {statistics.median(delays):.1f} samples\n")
            out.write(f"- P90 publication delay: {percentile(delays, 0.90):.1f} samples\n")
            out.write(f"- Maximum publication delay: {max(delays):.1f} samples\n\n")
        out.write("| Event | First control timestamp | Publication delay (samples) | Scheduled correction (cents) |\n")
        out.write("|---:|---:|---:|---:|\n")
        for row in rows:
            out.write(f"| {row['event']} | {row['timestamp']:.0f} | {row['delay']:.1f} | {row['scheduled']:.2f} |\n")
    print(report)


if __name__ == "__main__":
    main()
