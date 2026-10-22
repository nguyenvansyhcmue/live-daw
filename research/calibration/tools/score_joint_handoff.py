#!/usr/bin/env python3
"""Reject a handoff change that improves one Hook-2 event at another's expense.

Offline research gate only. The three events are fixed evaluation anchors, not
runtime branches or DSP parameters. Independent holdout audio is still needed.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


EVENT_SECONDS = (3.855604, 7.542271, 8.356937)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("artist", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidates", type=Path, nargs="+")
    parser.add_argument("--pitch-tools", type=Path, required=True)
    parser.add_argument(
        "--candidate-latency-delta-samples", type=int, default=0,
        help="Declared latency added by candidates relative to baseline/parent; keep all scores on the raw-file clock.",
    )
    parser.add_argument(
        "--gate-against", type=Path,
        help="Optional current research parent; keep the baseline clock but gate promotion against this stronger render.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    sys.path.insert(0, str(args.pitch_tools))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from compare_pitch_correction_bounces import pitch_track
    from fit_studioforge_transitions import event_rows
    from measure_artist_vibe_latency_aligned import envelope_delay, read_mono

    sample_rate, raw = read_mono(args.raw)
    artist_rate, artist = read_mono(args.artist)
    if artist_rate != sample_rate:
        raise ValueError("Artist and raw sample rates differ")

    artist_track = pitch_track(artist, sample_rate)
    artist_delay = envelope_delay(raw, artist, sample_rate)
    baseline_rate, baseline_signal = read_mono(args.baseline)
    if baseline_rate != sample_rate:
        raise ValueError("Baseline sample rate differs")
    baseline_delay = envelope_delay(raw, baseline_signal, sample_rate)
    artist_times = artist_track[:, 0] / sample_rate - artist_delay / sample_rate
    artist_valid = np.isfinite(artist_track[:, 1]) & (artist_track[:, 2] >= 0.55)

    def score(path: Path, candidate_latency_delta: int = 0) -> dict:
        rate, rendered = read_mono(path)
        if rate != sample_rate:
            raise ValueError(f"Sample-rate mismatch: {path}")
        # These variants have identical render origin and declared latency.
        # Freeze alignment once: independently refitting each candidate would
        # let a changed phrase move every other event's measured timestamp.
        fitted_delay = envelope_delay(raw, rendered, sample_rate)
        fixed_delay = lambda source, signal, rate: artist_delay if signal is artist else baseline_delay + candidate_latency_delta
        events, _, render_delay = event_rows(
            artist, rendered, sample_rate, fixed_delay, pitch_track, raw
        )
        anchors = []
        for anchor in EVENT_SECONDS:
            event = min(events, key=lambda row: abs(row["time_seconds"] - anchor))
            if abs(event["time_seconds"] - anchor) > 0.012:
                raise ValueError(f"No event near {anchor:.3f} s in {path}")
            anchors.append({
                "event_seconds": anchor,
                "t10_error_ms": event["vibe_minus_artist_t10_ms"],
                "t50_error_ms": event["vibe_minus_artist_t50_ms"],
                "t90_error_ms": event["vibe_minus_artist_t90_ms"],
                "span_error_ms": event["vibe_minus_artist_t90_ms"] - event["vibe_minus_artist_t10_ms"],
            })
        vibe_track = pitch_track(rendered, sample_rate)
        vibe_times = vibe_track[:, 0] / sample_rate - render_delay / sample_rate
        vibe_valid = np.isfinite(vibe_track[:, 1]) & (vibe_track[:, 2] >= 0.55)
        predicted = np.interp(
            artist_times[artist_valid], vibe_times[vibe_valid],
            vibe_track[vibe_valid, 1], left=np.nan, right=np.nan
        )
        reference = artist_track[artist_valid, 1]
        usable = np.isfinite(predicted) & (predicted > 0) & (reference > 0)
        cents = 1200.0 * np.log2(predicted[usable] / reference[usable])
        note_match = np.rint(69 + 12 * np.log2(predicted[usable] / 440.0)) == np.rint(
            69 + 12 * np.log2(reference[usable] / 440.0)
        )
        return {
            "render": str(path),
            "render_sha256": sha256(path),
            "raw_sha256": sha256(args.raw),
            "artist_sha256": sha256(args.artist),
            "fixed_alignment_samples": baseline_delay + candidate_latency_delta,
            "independently_fitted_delay_samples": fitted_delay,
            "events": anchors,
            "worst_abs_t90_ms": max(abs(row["t90_error_ms"]) for row in anchors),
            "median_abs_pitch_cents": float(np.median(np.abs(cents))),
            "p90_abs_pitch_cents": float(np.quantile(np.abs(cents), 0.9)),
            "same_note_fraction": float(np.mean(note_match)),
        }

    baseline = score(args.baseline)
    promotion_reference = score(args.gate_against) if args.gate_against else baseline
    results = [baseline]
    for candidate in args.candidates:
        result = score(candidate, args.candidate_latency_delta_samples)
        # One analysis frame (about 1.33 ms) is tolerated per event.
        result["joint_gate_pass"] = (
            all(abs(new[key]) <= abs(old[key]) + 1.334
                for new, old in zip(result["events"], baseline["events"])
                for key in ("t10_error_ms", "t50_error_ms", "t90_error_ms", "span_error_ms"))
            and result["worst_abs_t90_ms"] < baseline["worst_abs_t90_ms"]
            and result["p90_abs_pitch_cents"] <= baseline["p90_abs_pitch_cents"]
            and result["median_abs_pitch_cents"] <= baseline["median_abs_pitch_cents"]
            and result["same_note_fraction"] >= baseline["same_note_fraction"]
        )
        if args.gate_against:
            result["promotion_reference"] = str(args.gate_against)
            result["promotion_gate_pass"] = (
                all(abs(new[key]) <= abs(old[key]) + 1.334
                    for new, old in zip(result["events"], promotion_reference["events"])
                    for key in ("t10_error_ms", "t50_error_ms", "t90_error_ms", "span_error_ms"))
                and result["worst_abs_t90_ms"] < promotion_reference["worst_abs_t90_ms"]
                and result["p90_abs_pitch_cents"] <= promotion_reference["p90_abs_pitch_cents"]
                and result["median_abs_pitch_cents"] <= promotion_reference["median_abs_pitch_cents"]
                and result["same_note_fraction"] >= promotion_reference["same_note_fraction"]
            )
        results.append(result)
    payload = json.dumps(results, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    print(payload)


if __name__ == "__main__":
    main()
