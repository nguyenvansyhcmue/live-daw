#!/usr/bin/env python3
"""Summarize hard-tune-zero Artist/Vibe behaviour by controlled technique pair."""
from __future__ import annotations
import argparse
import csv
from pathlib import Path

FIELDS = ("retune_ms", "flex_tune", "humanize", "natural_vibrato")


def hard_tune_zero(report: Path) -> dict:
    with report.open(newline="") as source:
        for row in csv.DictReader(source):
            if all(abs(float(row[field])) < 1e-9 for field in FIELDS):
                return row
    raise ValueError(f"No all-zero control row: {report}")


def number(row: dict, field: str) -> float:
    return float(row[field])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    index = list(csv.DictReader((args.run_root / "run-index.csv").open(newline="")))
    groups = {}
    for row in index:
        report = Path(row["comparison"]).with_suffix(".csv")
        # report lives beside .md: .../comparison/calibration-report.csv
        report = Path(row["comparison"]).parent / "calibration-report.csv"
        groups.setdefault((row.get("dataset_voice", "unknown"), row["technique"], row["song"], row["clip"]), {})[row["group"]] = (row, hard_tune_zero(report))

    lines = ["# GTSinger Artist/Vibe hard-tune-zero summary", "", "All values select `Retune=0, Flex=0, Humanize=0, Natural Vibrato=0`. Values compare latency-aligned F0 trajectories; they do not compare waveform phase.", "", "| Singer | Technique | Clip | Control Δ cents | Technique Δ cents | Extra Δ | Control transitions A/V | Technique transitions A/V |", "|---|---|---|---:|---:|---:|---:|---:|"]
    for (dataset_voice, technique, song, clip), values in sorted(groups.items()):
        control_row, control = values["Control_Group"]
        technique_row, styled = values[f"{technique}_Group"]
        control_error = number(control, "vibe_minus_artist_f0_median_absolute_cents")
        styled_error = number(styled, "vibe_minus_artist_f0_median_absolute_cents")
        ca, cv = int(control["artist_transition_count"]), int(control["vibe_transition_count"])
        ta, tv = int(styled["artist_transition_count"]), int(styled["vibe_transition_count"])
        lines.append(f"| {dataset_voice} | {technique} | {song} #{clip} | {control_error:.2f} | {styled_error:.2f} | {styled_error-control_error:+.2f} | {ca}/{cv} | {ta}/{tv} |")
    lines.extend(["", "## Interpretation rule", "", "A technique-specific DSP change is eligible for a new A/B only if it reduces the technique's extra error and transition deficit without worsening the paired Control clip. This report is evidence, not a release-promotion decision."])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
