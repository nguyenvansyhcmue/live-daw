#!/usr/bin/env python3
"""Compare a research candidate against its parent on one independent vocal.

The parent establishes the raw-file clock. A candidate may not refit its own
delay to hide a timing change. This diagnostic never modifies audio or DSP.
"""

import argparse
import csv
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_renderer_control_parity(parent_trace: Path, candidate_trace: Path) -> dict:
    """Reject a purported renderer-only A/B with different musical controls."""
    fields = ("sampleIndex", "committedTargetMidi", "requestedRendererRatio")
    rows = 0
    with parent_trace.open(newline="") as parent_stream, candidate_trace.open(newline="") as candidate_stream:
        parent = csv.DictReader(parent_stream)
        candidate = csv.DictReader(candidate_stream)
        if not all(field in parent.fieldnames and field in candidate.fieldnames for field in fields):
            raise ValueError("control trace is missing a required field")
        for old, new in itertools.zip_longest(parent, candidate):
            if old is None or new is None:
                raise ValueError(f"control trace row count differs at row {rows}")
            for field in fields:
                if old[field] != new[field]:
                    raise ValueError(f"renderer-only control differs at row {rows}: {field}")
            rows += 1
    return {"rows": rows, "fields": list(fields), "identical": True}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--artist", type=Path, required=True)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--pitch-tools", type=Path, required=True)
    parser.add_argument("--artist-delay-samples", type=int,
                        help="Freeze the Artist alignment to a previously established raw-file clock")
    parser.add_argument("--parent-delay-samples", type=int,
                        help="Freeze parent and candidate to one previously established raw-file clock")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--event-rows", type=Path,
                        help="Optional sample-clock rows where rounded-note agreement changes")
    parser.add_argument("--reference-score", type=Path,
                        help="Require raw/Artist/parent SHA-256 to match an existing score")
    parser.add_argument("--parent-trace", type=Path)
    parser.add_argument("--candidate-trace", type=Path)
    args = parser.parse_args()
    if (args.parent_trace is None) != (args.candidate_trace is None):
        parser.error("--parent-trace and --candidate-trace must be supplied together")
    control_parity = (check_renderer_control_parity(args.parent_trace, args.candidate_trace)
                      if args.parent_trace is not None else None)

    sys.path.insert(0, str(args.pitch_tools))
    from compare_pitch_correction_bounces import pitch_track
    from measure_artist_vibe_latency_aligned import envelope_delay, read_mono

    rate, raw = read_mono(args.raw)
    signals = {}
    tracks = {}
    for label, path in (("artist", args.artist), ("parent", args.parent),
                        ("candidate", args.candidate)):
        current_rate, signal = read_mono(path)
        if current_rate != rate:
            raise ValueError(f"sample rate mismatch in {path}")
        signals[label] = signal
        tracks[label] = pitch_track(signal, rate)

    artist_fitted_delay = envelope_delay(raw, signals["artist"], rate)
    parent_fitted_delay = envelope_delay(raw, signals["parent"], rate)
    candidate_fitted_delay = envelope_delay(raw, signals["candidate"], rate)
    artist_delay = (args.artist_delay_samples if args.artist_delay_samples is not None
                    else artist_fitted_delay)
    parent_delay = (args.parent_delay_samples if args.parent_delay_samples is not None
                    else parent_fitted_delay)
    artist_track = tracks["artist"]
    reference_time = (artist_track[:, 0] - artist_delay) / rate
    reference_hz = artist_track[:, 1]
    reference_valid = np.isfinite(reference_hz) & (artist_track[:, 2] >= 0.55)

    predictions = {}
    validity = {}
    for label in ("parent", "candidate"):
        track = tracks[label]
        render_time = (track[:, 0] - parent_delay) / rate
        good = np.isfinite(track[:, 1]) & (track[:, 2] >= 0.55)
        predictions[label] = np.interp(
            reference_time, render_time[good], track[good, 1],
            left=np.nan, right=np.nan,
        ) if np.any(good) else np.full_like(reference_hz, np.nan)
        validity[label] = np.isfinite(predictions[label]) & (predictions[label] > 0.0)

    common = reference_valid & validity["parent"] & validity["candidate"]
    if int(np.count_nonzero(common)) < 32:
        raise ValueError("insufficient common voiced frames")
    target = reference_hz[common]
    errors = {}
    matches = {}
    result = {
        "sample_rate": rate,
        "common_voiced_frames": int(np.count_nonzero(common)),
        "artist_delay_samples": artist_delay,
        "parent_delay_samples": parent_delay,
        "artist_fitted_delay_samples": artist_fitted_delay,
        "parent_fitted_delay_samples": parent_fitted_delay,
        "candidate_fitted_delay_samples": candidate_fitted_delay,
        "candidate_clock_shift_samples": candidate_fitted_delay - parent_fitted_delay,
        "sha256": {label: sha256(path) for label, path in (
            ("raw", args.raw), ("artist", args.artist),
            ("parent", args.parent), ("candidate", args.candidate))},
    }
    if control_parity is not None:
        result["renderer_control_parity"] = control_parity
    if args.reference_score is not None:
        reference = json.loads(args.reference_score.read_text())
        for label in ("raw", "artist", "parent"):
            if result["sha256"][label] != reference["sha256"][label]:
                raise ValueError(f"{label} SHA-256 differs from reference score")
    for label in ("parent", "candidate"):
        predicted = predictions[label][common]
        errors[label] = np.abs(1200.0 * np.log2(predicted / target))
        matches[label] = np.rint(69.0 + 12.0 * np.log2(predicted / 440.0)) == np.rint(
            69.0 + 12.0 * np.log2(target / 440.0))
        result[label] = {
            "median_abs_pitch_cents": float(np.median(errors[label])),
            "p90_abs_pitch_cents": float(np.quantile(errors[label], 0.9)),
            "same_note_fraction": float(np.mean(matches[label])),
            "valid_pitch_frames": int(np.count_nonzero(reference_valid & validity[label])),
        }
    result["candidate_minus_parent"] = {
        "median_abs_pitch_cents": result["candidate"]["median_abs_pitch_cents"]
                                  - result["parent"]["median_abs_pitch_cents"],
        "p90_abs_pitch_cents": result["candidate"]["p90_abs_pitch_cents"]
                               - result["parent"]["p90_abs_pitch_cents"],
        "same_note_fraction": result["candidate"]["same_note_fraction"]
                              - result["parent"]["same_note_fraction"],
        "gained_matching_frames": int(np.count_nonzero(~matches["parent"] & matches["candidate"])),
        "lost_matching_frames": int(np.count_nonzero(matches["parent"] & ~matches["candidate"])),
    }
    if args.event_rows is not None:
        rows = []
        common_indices = np.flatnonzero(common)
        artist_midi = np.rint(69.0 + 12.0 * np.log2(target / 440.0))
        for local_index in np.flatnonzero(matches["parent"] != matches["candidate"]):
            reference_index = common_indices[local_index]
            row = {
                "raw_sample": int(round(reference_time[reference_index] * rate)),
                "raw_seconds": float(reference_time[reference_index]),
                "outcome": "gained" if matches["candidate"][local_index] else "lost",
                "artist_midi": int(artist_midi[local_index]),
            }
            for label in ("parent", "candidate"):
                hz = float(predictions[label][reference_index])
                row[f"{label}_midi"] = float(69.0 + 12.0 * np.log2(hz / 440.0))
                row[f"{label}_error_cents"] = float(errors[label][local_index])
            rows.append(row)
        args.event_rows.parent.mkdir(parents=True, exist_ok=True)
        with args.event_rows.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=[
                "raw_sample", "raw_seconds", "outcome", "artist_midi",
                "parent_midi", "parent_error_cents", "candidate_midi",
                "candidate_error_cents",
            ])
            writer.writeheader()
            writer.writerows(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
