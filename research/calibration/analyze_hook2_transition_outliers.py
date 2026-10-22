#!/usr/bin/env python3
"""Rank Artist-vs-Vibe transition mismatches without changing DSP."""
from __future__ import annotations

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def number(row: dict[str, str], key: str) -> float:
    return float(row[key])


def main(events_path: Path) -> None:
    with events_path.open(newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise SystemExit("no transition rows")

    for row in rows:
        row["score"] = (
            abs(number(row, "vibe_minus_artist_t50_ms"))
            + 0.5 * abs(number(row, "vibe_minus_artist_t90_ms"))
            + 0.15 * abs(abs(number(row, "artist_step_cents")) - abs(number(row, "vibe_step_cents")))
        )

    groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in ("retune_ms", "flex_tune", "humanize", "natural_vibrato"))].append(row)

    output = events_path.with_name("transition-outlier-report.md")
    lines = [
        "# Hook-2 transition outliers",
        "",
        "Scores combine t50/t90 timing disagreement and step-amplitude disagreement; they are ranking evidence, not a tuning target.",
        "",
        "## Worst control surfaces",
        "",
        "| Controls R/F/H/N | events | median score | worst score |",
        "|---|---:|---:|---:|",
    ]
    surface_rows = []
    for control, values in groups.items():
        scores = [float(value["score"]) for value in values]
        surface_rows.append((statistics.median(scores), max(scores), control, len(values)))
    for median, worst, control, count in sorted(surface_rows, reverse=True):
        lines.append(f"| {'/'.join(control)} | {count} | {median:.2f} | {worst:.2f} |")

    lines += [
        "",
        "## Highest-priority individual transitions",
        "",
        "| R/F/H/N | time | dir | Artist/Vibe step cents | Δt50 ms | Δt90 ms | score |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for row in sorted(rows, key=lambda value: float(value["score"]), reverse=True)[:30]:
        controls = "/".join(row[key] for key in ("retune_ms", "flex_tune", "humanize", "natural_vibrato"))
        lines.append(
            f"| {controls} | {number(row, 'time_seconds'):.3f} | {row['direction']} | "
            f"{number(row, 'artist_step_cents'):.1f}/{number(row, 'vibe_step_cents'):.1f} | "
            f"{number(row, 'vibe_minus_artist_t50_ms'):.1f} | "
            f"{number(row, 'vibe_minus_artist_t90_ms'):.1f} | {float(row['score']):.1f} |"
        )
    output.write_text("\n".join(lines) + "\n")
    print(output)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: analyze_hook2_transition_outliers.py <transition-events.csv>")
    main(Path(sys.argv[1]))
