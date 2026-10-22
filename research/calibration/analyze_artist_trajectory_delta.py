#!/usr/bin/env python3
"""Compare Artist's inferred correction curve with Vibe's delivered curve."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


def cents(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return 1200.0 * np.log2(a / b)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("artist", type=Path)
    parser.add_argument("intervals", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pitch-tools", type=Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.pitch_tools))
    from compare_pitch_correction_bounces import pitch_track
    from measure_artist_vibe_latency_aligned import envelope_delay, read_mono

    rate, raw = read_mono(args.raw)
    artist_rate, artist = read_mono(args.artist)
    if rate != artist_rate:
        raise SystemExit("sample-rate mismatch")
    raw_track = pitch_track(raw, rate)
    artist_track = pitch_track(artist, rate)
    raw_time = raw_track[:, 0] / rate
    artist_delay = envelope_delay(raw, artist, rate)
    artist_time = artist_track[:, 0] / rate - artist_delay / rate
    valid_raw = np.isfinite(raw_track[:, 1]) & (raw_track[:, 2] >= .55)
    valid_artist = np.isfinite(artist_track[:, 1]) & (artist_track[:, 2] >= .55)

    rows = []
    with args.intervals.open(newline="") as handle:
        for source in csv.DictReader(handle):
            try:
                if int(source["committedTargetMidi"]) < 0 or int(source["correctionIsActive"]) == 0:
                    continue
                control = float(source["deliveredRendererCorrectionCents"])
                time = float(source["timeMs"]) / 1000.0
            except (KeyError, ValueError):
                continue
            # A diagnostic row is written on the renderer/output timeline.
            # With current provenance telemetry, outputRendererControlTimestamp
            # identifies the source audio represented by that *audible* row.
            # It must take precedence over TD-PSOLA's source-control timestamp:
            # the latter belongs to the source-grain planner, not necessarily
            # the output ratio stream. Fall back compatibly for older traces.
            try:
                source_timestamp = int(source.get("outputRendererControlTimestamp",
                                                   source.get("sourceControlTimestamp", "-1")))
            except ValueError:
                source_timestamp = -1
            source_time = source_timestamp / rate if source_timestamp >= 0 else time
            raw_hz = np.interp(source_time, raw_time[valid_raw], raw_track[valid_raw, 1], left=np.nan, right=np.nan)
            artist_hz = np.interp(source_time, artist_time[valid_artist], artist_track[valid_artist, 1], left=np.nan, right=np.nan)
            if not (np.isfinite(raw_hz) and np.isfinite(artist_hz) and raw_hz > 0.0 and artist_hz > 0.0):
                continue
            artist_correction = float(cents(np.asarray([artist_hz]), np.asarray([raw_hz]))[0])
            # Reject octave detector disagreements; correction rail is ±160 ct.
            if abs(artist_correction) > 400.0 or abs(control) > 200.0:
                continue
            raw_midi = 69.0 + 12.0 * np.log2(raw_hz / 440.0)
            artist_target = int(np.rint(raw_midi + artist_correction / 100.0))
            rows.append({
                "time_seconds": f"{source_time:.6f}",
                "output_time_seconds": f"{time:.6f}",
                "raw_midi": f"{raw_midi:.4f}",
                "artist_inferred_target_midi": str(artist_target),
                "vibe_target_midi": source.get("outputRendererControlTargetMidi",
                                                  source["committedTargetMidi"]),
                "vibe_target_changed": source["targetChanged"],
                "artist_inferred_correction_cents": f"{artist_correction:.6f}",
                "vibe_delivered_correction_cents": f"{control:.6f}",
                "vibe_minus_artist_correction_cents": f"{control - artist_correction:.6f}",
                "vibe_trajectory_active": source["trajectoryTransitionActive"],
                "vibe_selector_decision": source["selectorDecision"],
                "vibe_ola_target_midi": source["olaDominantGrainTargetMidi"],
            })
    if not rows:
        raise SystemExit("no jointly reliable trajectory rows")
    delta = np.asarray([float(row["vibe_minus_artist_correction_cents"]) for row in rows])
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "artist-vibe-trajectory.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    worst = sorted(rows, key=lambda row: abs(float(row["vibe_minus_artist_correction_cents"])), reverse=True)[:16]
    report = [
        "# Artist-to-Vibe trajectory comparison", "",
        f"- Artist audio latency vs raw: {artist_delay} samples ({artist_delay / rate * 1000.0:.2f} ms)",
        f"- Reliable control points: {len(rows)}",
        "- Timing basis: `outputRendererControlTimestamp` when present (the source time of audible output control)",
        f"- Median |Vibe control − Artist inferred correction|: {np.median(np.abs(delta)):.2f} cents",
        f"- P90 |Vibe control − Artist inferred correction|: {np.quantile(np.abs(delta), .90):.2f} cents", "",
        "## Largest trajectory disagreements", "",
        "| Raw time | Raw MIDI | Artist target* | Vibe target | Artist ct | Vibe ct | Δ ct |", "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in worst:
        report.append("| {time_seconds} | {raw_midi} | {artist_inferred_target_midi} | {vibe_target_midi} | {artist_inferred_correction_cents} | {vibe_delivered_correction_cents} | {vibe_minus_artist_correction_cents} |".format(**row))
    (args.output / "artist-vibe-trajectory.md").write_text("\n".join(report) + "\n")
    print((args.output / "artist-vibe-trajectory.md").as_posix())


if __name__ == "__main__":
    main()
