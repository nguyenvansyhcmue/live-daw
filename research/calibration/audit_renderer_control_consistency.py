#!/usr/bin/env python3
"""Audit whether the renderer emits the correction of its causal control frame."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def value(row: dict[str, str], key: str) -> float:
    try:
        return float(row[key])
    except (KeyError, ValueError):
        return float("nan")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("intervals", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--sample-rate", type=float, default=48000.0)
    p.add_argument("--minimum-mismatch-cents", type=float, default=40.0)
    args = p.parse_args()

    rows: list[dict[str, str]] = []
    with args.intervals.open(newline="") as handle:
        for row in csv.DictReader(handle):
            expected = value(row, "sourceControlCorrectionAfter")
            delivered = value(row, "deliveredRendererCorrectionCents")
            source_time = value(row, "sourceControlTimestamp")
            valid = value(row, "sourceControlValid")
            hold_dry = value(row, "sourceControlHoldDry")
            if not (np.isfinite(expected) and np.isfinite(delivered)
                    and np.isfinite(source_time) and valid >= 1.0 and hold_dry == 0.0):
                continue
            difference = delivered - expected
            record = dict(row)
            record["source_time_seconds"] = f"{source_time / args.sample_rate:.6f}"
            record["control_to_delivery_delta_cents"] = f"{difference:.6f}"
            rows.append(record)

    if not rows:
        raise SystemExit("no valid source-control/rendered-control pairs")
    delta = np.asarray([value(row, "control_to_delivery_delta_cents") for row in rows])
    outliers = [row for row in rows if abs(value(row, "control_to_delivery_delta_cents")) >= args.minimum_mismatch_cents]
    outliers.sort(key=lambda row: abs(value(row, "control_to_delivery_delta_cents")), reverse=True)
    args.output.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with (args.output / "renderer-control-outliers.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(outliers[:500])
    report = [
        "# Renderer/control consistency audit", "",
        f"- Valid causal control/render pairs: {len(rows)}",
        f"- Median |delivered − source control|: {np.median(np.abs(delta)):.2f} cents",
        f"- P90 |delivered − source control|: {np.quantile(np.abs(delta), .90):.2f} cents",
        f"- Maximum |delivered − source control|: {np.max(np.abs(delta)):.2f} cents",
        f"- Pairs with ≥{args.minimum_mismatch_cents:.0f} cents mismatch: {len(outliers)}", "",
        "## Largest mismatches", "",
        "| Output time | Source-control time | Source correction | Delivered correction | Delta | Source target | Committed target |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in outliers[:20]:
        report.append("| {timeMs} | {source_time_seconds} | {sourceControlCorrectionAfter} | {deliveredRendererCorrectionCents} | {control_to_delivery_delta_cents} | {sourceControlTargetMidi} | {committedTargetMidi} |".format(**row))
    (args.output / "renderer-control-report.md").write_text("\n".join(report) + "\n")
    print(args.output / "renderer-control-report.md")


if __name__ == "__main__":
    main()
