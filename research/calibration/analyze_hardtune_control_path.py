#!/usr/bin/env python3
"""Audit hard-tune control delivery without altering DSP or audio files."""
from __future__ import annotations

import csv
import math
import statistics
import sys
from pathlib import Path


def number(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
        return value if math.isfinite(value) else math.nan
    except (KeyError, ValueError):
        return math.nan


def cents_from_ratio(ratio: float) -> float:
    return 1200.0 * math.log2(ratio) if ratio > 0.0 and math.isfinite(ratio) else math.nan


def median(values: list[float]) -> float:
    return statistics.median(values) if values else math.nan


def main(path: Path) -> None:
    with path.open(newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise SystemExit("empty signal-chain trace")

    active = [row for row in rows if row.get("correctionIsActive") == "1"]
    requested_minus_delivered: list[float] = []
    desired_minus_retune: list[float] = []
    active_without_delivery = 0
    for row in active:
        requested = cents_from_ratio(number(row, "requestedRendererRatio"))
        delivered = number(row, "deliveredRendererCorrectionCents")
        desired = number(row, "desiredCorrectionCents")
        retune = number(row, "retuneCorrectionCents")
        if math.isfinite(requested) and math.isfinite(delivered):
            requested_minus_delivered.append(abs(requested - delivered))
            if abs(requested) >= 10.0 and abs(delivered) < 2.5:
                active_without_delivery += 1
        if math.isfinite(desired) and math.isfinite(retune):
            desired_minus_retune.append(abs(desired - retune))

    # `targetChanged` is a frame-level telemetry flag and can remain high for
    # several audio-control rows. A real commit is a change of the discrete
    # committed MIDI value, not a rising edge of that flag.
    commits = []
    previous_target: int | None = None
    for index, row in enumerate(rows):
        try:
            target = int(float(row.get("committedTargetMidi", "-1")))
        except ValueError:
            target = -1
        if target >= 0 and target != previous_target:
            commits.append(index)
        previous_target = target if target >= 0 else None

    windows = []
    for start in commits:
        first = rows[start]
        begin_ms = number(first, "timeMs")
        window = [row for row in rows[start:] if number(row, "timeMs") <= begin_ms + 30.0]
        values = [abs(number(row, "deliveredRendererCorrectionCents")) for row in window]
        values = [value for value in values if math.isfinite(value)]
        active_count = sum(row.get("correctionIsActive") == "1" for row in window)
        windows.append((begin_ms, first.get("selectorPreviousTarget", "?"),
                        first.get("committedTargetMidi", "?"), active_count, max(values, default=math.nan)))

    output = path.with_name("hard-tune-control-path.md")
    with output.open("w") as report:
        report.write("# Hard-tune control-path audit\n\n")
        report.write("This measures internal requested-to-delivered control only; it does not claim an audio result.\n\n")
        report.write(f"- Trace rows: {len(rows)}\n")
        report.write(f"- Correction-active rows: {len(active)}\n")
        report.write(f"- Median |requested renderer cents − delivered cents|: {median(requested_minus_delivered):.2f}\n")
        report.write(f"- P90 |requested renderer cents − delivered cents|: "
                     f"{(sorted(requested_minus_delivered)[max(0, math.ceil(.90 * len(requested_minus_delivered)) - 1)] if requested_minus_delivered else math.nan):.2f}\n")
        report.write(f"- Active rows requesting >=10 cents but delivering <2.5 cents: {active_without_delivery}\n")
        report.write(f"- Median |desired correction − trajectory correction|: {median(desired_minus_retune):.2f} cents\n")
        report.write(f"- Discrete target commits: {len(commits)}\n\n")
        report.write("## First 30 ms after each discrete target commit\n\n")
        report.write("| time ms | from | to | active rows | peak delivered cents |\n|---:|---:|---:|---:|---:|\n")
        for time_ms, old, new, active_count, peak in windows:
            report.write(f"| {time_ms:.2f} | {old} | {new} | {active_count} | {peak:.2f} |\n")
    print(output)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: analyze_hardtune_control_path.py <full_default_intervals.csv>")
    main(Path(sys.argv[1]))
