#!/usr/bin/env python3
"""Classify Artist-vs-Vibe transition outliers using Vibe control provenance.

This is measurement only.  It prevents a score produced at a voiced/unvoiced
boundary or amid several note commits from being mistaken for a DSP defect.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path


def number(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except ValueError:
        return default


def main(events_file: Path, controls_file: Path, output_file: Path) -> None:
    with events_file.open(newline="") as handle:
        events = list(csv.DictReader(handle))
    with controls_file.open(newline="") as handle:
        controls = list(csv.DictReader(handle))

    rows: list[dict[str, object]] = []
    for event in events:
        event_ms = number(event, "time_seconds") * 1000.0
        # The pitch-transition scorer uses a roughly 200-ms stable post area.
        # Inspect the matching 110-ms decision window either side of its onset.
        window = [r for r in controls if event_ms - 110.0 <= number(r, "time_ms") <= event_ms + 110.0]
        commits = sum(int(number(r, "target_changed")) for r in window)
        unvoiced = sum(1 for r in window if not (number(r, "confidence", -1.0) >= 0.0))
        targets = [int(number(r, "target")) for r in window if int(number(r, "target")) >= 0]
        distinct_targets = len(set(targets))
        target_span = max(targets) - min(targets) if targets else 0
        score = (abs(number(event, "vibe_minus_artist_t50_ms"))
                 + 0.5 * abs(number(event, "vibe_minus_artist_t90_ms"))
                 + 0.15 * abs(abs(number(event, "artist_step_cents"))
                              - abs(number(event, "vibe_step_cents"))))
        if unvoiced:
            classification = "voiced-boundary: do not force wet correction"
        elif commits >= 2 or distinct_targets >= 3:
            classification = "multiple target commits: evaluate phrase grouping"
        elif commits == 1:
            classification = "single commit: trajectory/delivery candidate"
        else:
            classification = "no nearby commit: pitch-measurement association candidate"
        rows.append({
            "time_s": f"{event_ms / 1000.0:.3f}",
            "score": score,
            "artist_step_ct": number(event, "artist_step_cents"),
            "vibe_step_ct": number(event, "vibe_step_cents"),
            "dt50_ms": number(event, "vibe_minus_artist_t50_ms"),
            "dt90_ms": number(event, "vibe_minus_artist_t90_ms"),
            "commits": commits,
            "unvoiced_rows": unvoiced,
            "distinct_targets": distinct_targets,
            "target_span_semitones": target_span,
            "classification": classification,
        })

    rows.sort(key=lambda row: float(row["score"]), reverse=True)
    lines = [
        "# Hook-2 hard-tune transition provenance",
        "",
        "This report joins rendered-pitch outliers to Vibe's control trace. It does not change audio behaviour.",
        "",
        "| time | score | Artist/Vibe ct | Δt50/Δt90 ms | commits | unvoiced rows | targets | classification |",
        "|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows[:30]:
        lines.append(
            f"| {row['time_s']} | {float(row['score']):.1f} | "
            f"{float(row['artist_step_ct']):.1f}/{float(row['vibe_step_ct']):.1f} | "
            f"{float(row['dt50_ms']):.1f}/{float(row['dt90_ms']):.1f} | "
            f"{row['commits']} | {row['unvoiced_rows']} | "
            f"{row['distinct_targets']} ({row['target_span_semitones']} st) | {row['classification']} |"
        )
    output_file.write_text("\n".join(lines) + "\n")
    print(output_file)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: audit_hook2_transition_provenance.py <transition-events.csv> <focused-controls.csv> <output.md>")
    main(*(Path(arg) for arg in sys.argv[1:]))
