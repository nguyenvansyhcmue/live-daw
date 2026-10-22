#!/usr/bin/env python3
"""Measure target-commit to rendered-pitch delivery from a SignalChain trace.

This is deliberately a diagnostic, not an optimiser: it does not modify the
plugin.  It answers whether target selection or renderer delivery is the
source of a missed/late audible note.
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import numpy as np

DAW_TOOLS = Path("/Users/hiimdrdey/code/daw/autotune/tools")
sys.path.insert(0, str(DAW_TOOLS))
from compare_pitch_correction_bounces import pitch_track, read_mono  # noqa: E402


def note_for_hz(hz: float) -> float:
    return 69.0 + 12.0 * math.log2(hz / 440.0)


def parse_commits(events: Path):
    commits: list[tuple[int, int]] = []
    previous = -1
    with events.open(newline="") as source:
        for row in csv.DictReader(source):
            if row["event"] != "target_commit":
                continue
            target = int(row["detail"])
            if previous >= 0 and target != previous:
                commits.append((int(row["sampleIndex"]), target))
            previous = target
    return commits


def parse_control_trace(intervals: Path):
    rows = []
    with intervals.open(newline="") as source:
        for row in csv.DictReader(source):
            try:
                rows.append((int(float(row["sampleIndex"])), float(row["rawF0"]), float(row["stableF0"])))
            except (KeyError, ValueError):
                continue
    return rows


def analyze(case_dir: Path) -> None:
    sample_rate, audio = read_mono(case_dir / "full_default_render.wav")
    trace = pitch_track(audio, sample_rate)
    valid = [(int(sample), note_for_hz(float(hz))) for sample, hz, confidence in trace
             if math.isfinite(hz) and confidence >= 0.55]
    # Same sustained >=25-cent event rule as the Artist/Vibe calibration
    # report, but applied to this single renderer diagnostic.
    rendered_transitions = 0
    if len(valid) > 1:
        transition_start = None
        for index, changed in enumerate(np.r_[np.abs(np.diff([m for _, m in valid])) * 100.0 >= 25.0, False]):
            if changed and transition_start is None:
                transition_start = index
            elif not changed and transition_start is not None:
                end = index
                duration = (valid[end][0] - valid[transition_start][0]) / sample_rate
                cents = abs(valid[end][1] - valid[transition_start][1]) * 100.0
                if duration >= 0.004 and cents >= 25.0:
                    rendered_transitions += 1
                transition_start = None
    commits = parse_commits(case_dir / "full_default_events.csv")
    control = parse_control_trace(case_dir / "full_default_intervals.csv")
    rows = []
    previous_target = None
    for index, (commit_sample, target) in enumerate(commits):
        next_sample = commits[index + 1][0] if index + 1 < len(commits) else commit_sample + int(0.150 * sample_rate)
        if previous_target is None:
            previous_target = target
            continue
        onset = None
        consecutive = 0
        for sample, midi in valid:
            if sample < commit_sample or sample > min(next_sample, commit_sample + int(0.150 * sample_rate)):
                continue
            # A delivery must move at least 15 cents nearer to the new target
            # than to the immediately preceding target, for two pitch frames.
            closer = abs(midi - target) + 0.15 < abs(midi - previous_target)
            consecutive = consecutive + 1 if closer else 0
            if consecutive >= 2:
                onset = sample
                break
        latency_ms = "" if onset is None else 1000.0 * (onset - commit_sample) / sample_rate
        rows.append({"commit_sample": commit_sample, "commit_ms": 1000.0 * commit_sample / sample_rate,
                     "from_midi": previous_target, "to_midi": target,
                     "audible_sample": "" if onset is None else onset,
                     "delivery_ms": latency_ms})
        previous_target = target

    output = case_dir / "selector-delivery.csv"
    with output.open("w", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]) if rows else ["commit_sample"])
        writer.writeheader()
        writer.writerows(rows)
    values = [float(row["delivery_ms"]) for row in rows if row["delivery_ms"] != ""]
    missing = len(rows) - len(values)
    report = case_dir / "selector-delivery-summary.md"
    report.write_text(
        "# Target selector → rendered pitch delivery\n\n"
        f"- Distinct committed note changes: {len(rows)}\n"
        f"- Rendered pitch transitions (calibration rule): {rendered_transitions}\n"
        f"- Delivered within 150 ms: {len(values)}\n"
        f"- Not observed before next target/150 ms: {missing}\n"
        + (f"- Median commit-to-audible delivery: {np.median(values):.2f} ms\n"
           f"- P90 commit-to-audible delivery: {np.percentile(values, 90):.2f} ms\n"
           if values else "- No valid delivered note changes observed.\n")
    )
    # Determine whether a target waits after the raw/stable F0 has already
    # crossed the target midpoint.  This identifies detector lag without
    # conflating it with renderer latency measured above.
    detector_rows = []
    previous_target = None
    lookback = int(0.100 * sample_rate)
    for commit_sample, target in commits:
        if previous_target is None:
            previous_target = target
            continue
        direction = 1 if target > previous_target else -1
        midpoint = 0.5 * (target + previous_target)
        candidates = [row for row in control if commit_sample - lookback <= row[0] <= commit_sample]
        result = {"commit_sample": commit_sample, "from_midi": previous_target, "to_midi": target,
                  "raw_cross_lead_ms": "", "stable_cross_lead_ms": ""}
        for name, column in (("raw_cross_lead_ms", 1), ("stable_cross_lead_ms", 2)):
            crossings = [sample for sample, raw, stable in candidates
                         if math.isfinite((raw, stable)[column - 1])
                         and (note_for_hz((raw, stable)[column - 1]) - midpoint) * direction >= 0.0]
            if crossings:
                # The latest crossing is the conservative lead-in, avoiding
                # an unrelated earlier note during a fast phrase.
                result[name] = 1000.0 * (commit_sample - crossings[-1]) / sample_rate
        detector_rows.append(result)
        previous_target = target
    with (case_dir / "selector-detector-lead.csv").open("w", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(detector_rows[0]) if detector_rows else ["commit_sample"])
        writer.writeheader(); writer.writerows(detector_rows)
    raw_leads = [float(x["raw_cross_lead_ms"]) for x in detector_rows if x["raw_cross_lead_ms"] != ""]
    stable_leads = [float(x["stable_cross_lead_ms"]) for x in detector_rows if x["stable_cross_lead_ms"] != ""]
    with report.open("a") as destination:
        destination.write("\n## Detector midpoint → target commit\n\n")
        destination.write(f"- Raw F0 crossings observed: {len(raw_leads)}/{len(detector_rows)}\n")
        destination.write(f"- Stable F0 crossings observed: {len(stable_leads)}/{len(detector_rows)}\n")
        if raw_leads:
            destination.write(f"- Median raw-cross-to-commit: {np.median(raw_leads):.2f} ms\n")
        if stable_leads:
            destination.write(f"- Median stable-cross-to-commit: {np.median(stable_leads):.2f} ms\n")
    print(report)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: analyze_hook2_selector_delivery.py <signal-chain-case-directory>")
    analyze(Path(sys.argv[1]))
