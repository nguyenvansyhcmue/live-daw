#!/usr/bin/env python3
"""Join an Artist/Vibe pitch-transition comparison to Vibe's control trace.

This is an offline diagnostic only.  It does not modify a plug-in or render
audio.  Its purpose is to avoid tuning one global transition time for three
different musical situations (a sustained jump, a luyến/return, and a weak-F0
handoff).
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys

import numpy as np


def as_float(value: str, default: float = float("nan")) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def rising_commits(rows: list[dict[str, str]]) -> list[dict[str, float | int | str]]:
    commits = []
    was_changed = False
    previous_target: int | None = None
    for row in rows:
        changed = row.get("targetChanged") == "1"
        if changed and not was_changed:
            target = int(row["committedTargetMidi"])
            if previous_target is not None and target != previous_target:
                commits.append({
                    "commit_ms": as_float(row["timeMs"]),
                    "target": target,
                    "previous_target": previous_target,
                    "distance_semitones": target - previous_target,
                    "confidence": as_float(row.get("pitchConfidence", "")),
                    "motion_cents_per_second": as_float(row.get("instantaneousInputMotionCentsPerSecond", "")),
                    "transition_duration_ms": as_float(row.get("trajectoryTransitionDurationMs", "")),
                })
            previous_target = target
        elif changed:
            previous_target = int(row["committedTargetMidi"])
        was_changed = changed
    return commits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("event_csv", type=pathlib.Path)
    parser.add_argument("trace_csv", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument("--latency-samples", type=float, default=1152.0)
    parser.add_argument("--sample-rate", type=float, default=48000.0)
    args = parser.parse_args()

    with args.event_csv.open(newline="") as handle:
        events = list(csv.DictReader(handle))
    with args.trace_csv.open(newline="") as handle:
        trace_rows = list(csv.DictReader(handle))
    commits = rising_commits(trace_rows)
    latency_ms = args.latency_samples * 1000.0 / args.sample_rate
    # One ornament can yield several tracker movements. Attribute at most one
    # measured event to a commit, and only after that commit reaches the
    # fixed-latency audible timeline.
    matched: dict[float, tuple[float, dict[str, str], dict[str, float | int | str]]] = {}
    for event in events:
        event_ms = as_float(event["time_seconds"]) * 1000.0
        # Trace timestamps are at the input/control edge.  Bring them to the
        # audible timeline before matching waveform-derived events.
        commit = min(commits, key=lambda c: abs((c["commit_ms"] + latency_ms) - event_ms), default=None)
        if commit is None:
            continue
        audible_commit_ms = float(commit["commit_ms"]) + latency_ms
        delta = event_ms - audible_commit_ms
        if delta < 0.0 or delta > 50.0:
            continue
        previous = matched.get(float(commit["commit_ms"]))
        if previous is None or delta < previous[0]:
            matched[float(commit["commit_ms"])] = (delta, event, commit)

    out = []
    for delta, event, commit in matched.values():
        event_ms = as_float(event["time_seconds"]) * 1000.0
        prior = [c for c in commits if c["commit_ms"] < commit["commit_ms"]]
        previous_gap = commit["commit_ms"] - prior[-1]["commit_ms"] if prior else float("nan")
        artist_t10 = as_float(event["artist_t10_ms"])
        artist_t90 = as_float(event["artist_t90_ms"])
        vibe_t10 = as_float(event["vibe_t10_ms"])
        vibe_t90 = as_float(event["vibe_t90_ms"])
        out.append({
            "artist_event_ms": round(event_ms, 3),
            "direction": event["direction"],
            "target_commit_ms": round(float(commit["commit_ms"]), 3),
            "commit_to_event_ms": round(delta, 3),
            "distance_semitones": commit["distance_semitones"],
            "prior_commit_gap_ms": round(previous_gap, 3),
            "confidence": round(float(commit["confidence"]), 4),
            "motion_cents_per_second": round(float(commit["motion_cents_per_second"]), 3),
            "control_transition_ms": round(float(commit["transition_duration_ms"]), 3),
            "artist_handoff_ms": round(artist_t90 - artist_t10, 3),
            "vibe_handoff_ms": round(vibe_t90 - vibe_t10, 3),
            "vibe_minus_artist_handoff_ms": round((vibe_t90 - vibe_t10) - (artist_t90 - artist_t10), 3),
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(out[0]) if out else ["artist_event_ms"]
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out)
    print(f"matched_events={len(out)} output={args.output}")


if __name__ == "__main__":
    main()
