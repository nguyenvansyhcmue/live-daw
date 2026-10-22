#!/usr/bin/env python3
"""Verify the output-stage renderer control provenance in a diagnostic CSV."""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import numpy as np


def cents(ratio: float) -> float:
    return 1200.0 * math.log2(ratio) if math.isfinite(ratio) and ratio > 0.0 else float("nan")


def f(row: dict[str, str], name: str) -> float:
    try:
        return float(row[name])
    except (KeyError, ValueError):
        return float("nan")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("intervals", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    with args.intervals.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"outputRendererControlTimestamp", "outputRendererControlPitchRatio",
                "requestedRendererRatio", "deliveredRendererCorrectionCents", "sampleIndex"}
    missing = required - set(rows[0] if rows else {})
    if missing:
        raise SystemExit("trace is missing output-control telemetry: " + ", ".join(sorted(missing)))

    pairs = []
    delivery = []
    for row in rows:
        control = cents(f(row, "outputRendererControlPitchRatio"))
        requested = cents(f(row, "requestedRendererRatio"))
        delivered = f(row, "deliveredRendererCorrectionCents")
        if math.isfinite(control) and math.isfinite(requested):
            pairs.append((control, requested, row))
        if math.isfinite(requested) and math.isfinite(delivered) and f(row, "correctionIsActive") >= 1:
            delivery.append((delivered - requested, row))
    if not pairs:
        raise SystemExit("no valid output control pairs")
    requested_delta = np.asarray([requested - control for control, requested, _ in pairs])
    delivery_delta = np.asarray([delta for delta, _ in delivery])
    args.output.mkdir(parents=True, exist_ok=True)
    outliers = sorted(delivery, key=lambda item: abs(item[0]), reverse=True)[:40]
    report = [
        "# Output renderer-control provenance", "",
        f"- Output control/request pairs: {len(pairs)}",
        f"- Max |requested ratio − output-control ratio|: {np.max(np.abs(requested_delta)):.4f} cents",
        f"- Median |delivered − requested| while wet: {np.median(np.abs(delivery_delta)):.2f} cents",
        f"- P90 |delivered − requested| while wet: {np.quantile(np.abs(delivery_delta), .90):.2f} cents",
        "- Delivery difference is expected during a bounded transition; it is not by itself a stale-control fault.", "",
        "## Largest active delivery gaps", "",
        "| Output ms | Output control timestamp | Control ct | Requested ct | Delivered ct | Δ delivered/requested |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for delta, row in outliers:
        control = cents(f(row, "outputRendererControlPitchRatio"))
        requested = cents(f(row, "requestedRendererRatio"))
        report.append(f"| {f(row, 'timeMs'):.3f} | {row['outputRendererControlTimestamp']} | {control:.3f} | {requested:.3f} | {f(row, 'deliveredRendererCorrectionCents'):.3f} | {delta:.3f} |")
    (args.output / "output-renderer-control-report.md").write_text("\n".join(report) + "\n")
    print(args.output / "output-renderer-control-report.md")


if __name__ == "__main__":
    main()
