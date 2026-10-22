#!/usr/bin/env python3
"""Score confirmed-landing renders against one Artist reference.

This combines whole-take pitch agreement with a deliberately conservative
transition subset.  The subset rejects events whose measured 10--90 % span
is missing, starts before the detected event, or is wider than 40 ms.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("artist", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pitch-tools", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, action="append", required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.pitch_tools))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from compare_pitch_correction_bounces import cents, pitch_track
    from fit_studioforge_transitions import event_rows
    from measure_artist_vibe_latency_aligned import envelope_delay, read_mono

    sample_rate, raw = read_mono(args.raw)
    artist_rate, artist = read_mono(args.artist)
    if sample_rate != artist_rate:
        raise RuntimeError("sample-rate mismatch")

    renders = [("baseline", args.baseline)]
    for root in args.candidate_root:
        for directory in sorted(path for path in root.iterdir() if path.is_dir()):
            render = directory / "render/full_default_render.wav"
            if render.is_file():
                renders.append((directory.name, render))

    artist_track = pitch_track(artist, sample_rate)
    artist_delay = envelope_delay(raw, artist, sample_rate)
    artist_time = artist_track[:, 0] / sample_rate - artist_delay / sample_rate
    valid_artist = np.isfinite(artist_track[:, 1]) & (artist_track[:, 2] >= 0.55)
    rows = []
    detailed_events = []
    for name, render in renders:
        render_rate, signal = read_mono(render)
        if render_rate != sample_rate:
            raise RuntimeError(f"sample-rate mismatch: {render}")
        events, _, vibe_delay = event_rows(
            artist, signal, sample_rate, envelope_delay, pitch_track, raw
        )
        clean = []
        for event in events:
            artist_hold = event["artist_t10_ms"] - event["time_seconds"] * 1000.0
            vibe_hold = event["vibe_t10_ms"] - event["time_seconds"] * 1000.0
            artist_span = event["artist_t90_ms"] - event["artist_t10_ms"]
            vibe_span = event["vibe_t90_ms"] - event["vibe_t10_ms"]
            is_clean = (0.0 <= artist_hold <= 50.0 and 0.0 <= vibe_hold <= 50.0
                        and 0.0 < artist_span <= 40.0 and 0.0 < vibe_span <= 40.0)
            detailed_events.append({"candidate": name, "clean": int(is_clean), **event})
            if is_clean:
                artist_slope = 0.8 * abs(event["artist_step_cents"]) / artist_span
                vibe_slope = 0.8 * abs(event["vibe_step_cents"]) / vibe_span
                clean.append((event, artist_slope, vibe_slope))

        vibe_track = pitch_track(signal, sample_rate)
        vibe_time = vibe_track[:, 0] / sample_rate - vibe_delay / sample_rate
        valid_vibe = np.isfinite(vibe_track[:, 1]) & (vibe_track[:, 2] >= 0.55)
        queried = np.interp(
            artist_time[valid_artist], vibe_time[valid_vibe], vibe_track[valid_vibe, 1],
            left=np.nan, right=np.nan
        )
        artist_hz = artist_track[valid_artist, 1]
        usable = np.isfinite(queried) & (artist_hz > 0.0) & (queried > 0.0)
        error = cents(queried[usable], artist_hz[usable])
        notes_match = (
            np.rint(69.0 + 12.0 * np.log2(queried[usable] / 440.0))
            == np.rint(69.0 + 12.0 * np.log2(artist_hz[usable] / 440.0))
        )
        rows.append({
            "candidate": name,
            "events": len(events),
            "clean_events": len(clean),
            "vibe_delay_samples": vibe_delay,
            "same_note_fraction": float(np.mean(notes_match)),
            "median_abs_pitch_cents": float(np.median(np.abs(error))),
            "p90_abs_pitch_cents": float(np.quantile(np.abs(error), 0.90)),
            "median_abs_slope_error_cents_per_ms": float(np.median(
                [abs(vibe_slope - artist_slope) for _, artist_slope, vibe_slope in clean]
            )) if clean else float("nan"),
            "median_abs_t10_error_ms": float(np.median(
                [abs(event["vibe_minus_artist_t10_ms"]) for event, _, _ in clean]
            )) if clean else float("nan"),
            "median_abs_t90_error_ms": float(np.median(
                [abs(event["vibe_minus_artist_t90_ms"]) for event, _, _ in clean]
            )) if clean else float("nan"),
        })

    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
    if detailed_events:
        with (args.output / "events.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=detailed_events[0].keys())
            writer.writeheader()
            writer.writerows(detailed_events)
    for row in rows:
        print(json.dumps(row, sort_keys=True))


if __name__ == "__main__":
    main()
