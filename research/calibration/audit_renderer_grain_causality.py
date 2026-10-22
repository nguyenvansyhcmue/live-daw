#!/usr/bin/env python3
"""Audit exact target-commit to dominant-grain handoff from renderer telemetry."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("intervals", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    with args.intervals.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    events = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if row["targetChanged"] != "1" or row["rendererControlEventId"] in seen:
            continue
        event_id = row["rendererControlEventId"]
        seen.add(event_id)
        target = int(row["committedTargetMidi"])
        if target < 0:
            continue
        first = next((candidate for candidate in rows[index:]
                      if int(candidate["olaDominantGrainTargetMidi"]) == target), None)
        if first is None:
            continue
        commit_sample = int(row["sampleIndex"])
        first_sample = int(first["sampleIndex"])
        source_sample = int(row["sourceControlTimestamp"])
        events.append({
            "event_id": event_id,
            "commit_time_ms": row["timeMs"],
            "target_midi": str(target),
            "commit_to_dominant_samples": str(first_sample - commit_sample),
            "commit_to_dominant_ms": f"{(first_sample - commit_sample) / 48.0:.3f}",
            "source_control_to_dominant_samples": str(first_sample - source_sample),
            "source_control_to_dominant_ms": f"{(first_sample - source_sample) / 48.0:.3f}",
            "control_lookup_delta_samples": row["controlLookupDeltaSamples"],
        })
    if not events:
        raise SystemExit("no target commits with a subsequent dominant grain")
    handoffs = np.asarray([float(row["commit_to_dominant_samples"]) for row in events])
    lookup = np.asarray([float(row["control_lookup_delta_samples"]) for row in events])
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "grain-causality-events.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(events[0]))
        writer.writeheader()
        writer.writerows(events)
    report = [
        "# Renderer grain causality audit", "",
        f"- Target commits audited: {len(events)}",
        f"- Commit → new dominant grain median: {np.median(handoffs):.0f} samples ({np.median(handoffs) / 48.0:.2f} ms)",
        f"- Commit → new dominant grain P90: {np.quantile(handoffs, .90):.0f} samples ({np.quantile(handoffs, .90) / 48.0:.2f} ms)",
        f"- Max |control lookup timestamp delta|: {np.max(np.abs(lookup)):.0f} samples", "",
        "A small commit-to-grain interval and zero lookup delta rule out a stale control queue or old dominant grain as the cause of a later audible mismatch.",
    ]
    (args.output / "grain-causality-report.md").write_text("\n".join(report) + "\n")
    print((args.output / "grain-causality-report.md").as_posix())


if __name__ == "__main__":
    main()
