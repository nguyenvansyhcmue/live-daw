#!/usr/bin/env python3
"""Export an independently latency-aligned raw/Artist/Vibe pitch window.

The transition summary ranks disagreements, but a ranked event can be either
a late target handoff or a different *continuous correction contour* while
the target has not changed.  This tool makes that distinction explicit before
changing the selector or renderer.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


def interpolate_valid(track: np.ndarray, times: np.ndarray, query: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    valid = np.isfinite(track[:, 1]) & (track[:, 2] >= 0.55)
    if valid.sum() < 2:
        return np.full(query.shape, np.nan), np.full(query.shape, np.nan)
    return (
        np.interp(query, times[valid], track[valid, 1], left=np.nan, right=np.nan),
        np.interp(query, times[valid], track[valid, 2], left=np.nan, right=np.nan),
    )


def midi(hz: np.ndarray) -> np.ndarray:
    return 69.0 + 12.0 * np.log2(hz / 440.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("artist", type=Path)
    parser.add_argument("vibe", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pitch-tools", type=Path, required=True)
    parser.add_argument("--start", type=float, default=4.20)
    parser.add_argument("--end", type=float, default=4.85)
    args = parser.parse_args()
    if args.end <= args.start:
        raise SystemExit("--end must be later than --start")

    sys.path.insert(0, str(args.pitch_tools))
    from compare_pitch_correction_bounces import cents, pitch_track
    from measure_artist_vibe_latency_aligned import envelope_delay, read_mono

    rate, raw = read_mono(args.raw)
    artist_rate, artist = read_mono(args.artist)
    vibe_rate, vibe = read_mono(args.vibe)
    if rate != artist_rate or rate != vibe_rate:
        raise SystemExit("sample-rate mismatch")

    raw_track = pitch_track(raw, rate)
    artist_track = pitch_track(artist, rate)
    vibe_track = pitch_track(vibe, rate)
    raw_times = raw_track[:, 0] / rate
    artist_delay = envelope_delay(raw, artist, rate)
    vibe_delay = envelope_delay(raw, vibe, rate)
    artist_times = artist_track[:, 0] / rate - artist_delay / rate
    vibe_times = vibe_track[:, 0] / rate - vibe_delay / rate
    artist_hz, artist_conf = interpolate_valid(artist_track, artist_times, raw_times)
    vibe_hz, vibe_conf = interpolate_valid(vibe_track, vibe_times, raw_times)

    raw_hz, raw_conf = raw_track[:, 1], raw_track[:, 2]
    usable = (
        (raw_times >= args.start) & (raw_times <= args.end)
        & np.isfinite(raw_hz) & np.isfinite(artist_hz) & np.isfinite(vibe_hz)
        & (raw_hz > 0.0) & (artist_hz > 0.0) & (vibe_hz > 0.0)
        & (raw_conf >= 0.55) & (artist_conf >= 0.55) & (vibe_conf >= 0.55)
    )
    if not np.any(usable):
        raise SystemExit("no jointly reliable F0 frames in requested window")

    raw_midi = midi(raw_hz[usable])
    artist_midi = midi(artist_hz[usable])
    vibe_midi = midi(vibe_hz[usable])
    artist_move = cents(artist_hz[usable], raw_hz[usable])
    vibe_move = cents(vibe_hz[usable], raw_hz[usable])
    delta = cents(vibe_hz[usable], artist_hz[usable])

    args.output.mkdir(parents=True, exist_ok=True)
    csv_path = args.output / "pitch-window.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "raw_time_seconds", "raw_hz", "raw_midi", "raw_confidence",
            "artist_hz", "artist_midi", "artist_confidence", "artist_minus_raw_cents",
            "vibe_hz", "vibe_midi", "vibe_confidence", "vibe_minus_raw_cents",
            "vibe_minus_artist_cents",
        ])
        for index, time in enumerate(raw_times[usable]):
            writer.writerow([
                f"{time:.9f}", raw_hz[usable][index], raw_midi[index], raw_conf[usable][index],
                artist_hz[usable][index], artist_midi[index], artist_conf[usable][index], artist_move[index],
                vibe_hz[usable][index], vibe_midi[index], vibe_conf[usable][index], vibe_move[index], delta[index],
            ])

    peak = int(np.argmax(np.abs(delta)))
    report = [
        "# Hook-2 pitch-window forensic report",
        "",
        f"- Window: {args.start:.3f}–{args.end:.3f} s on the raw timeline",
        f"- Artist delay vs raw: {artist_delay} samples ({artist_delay / rate * 1000.0:.2f} ms)",
        f"- Vibe delay vs raw: {vibe_delay} samples ({vibe_delay / rate * 1000.0:.2f} ms)",
        f"- Jointly reliable frames: {len(delta)}",
        f"- Median |Vibe − Artist|: {np.median(np.abs(delta)):.2f} cents",
        f"- P90 |Vibe − Artist|: {np.quantile(np.abs(delta), .90):.2f} cents",
        f"- Largest difference: {delta[peak]:.2f} cents at {raw_times[usable][peak]:.6f} s",
        f"- At that point, Artist correction relative to raw: {artist_move[peak]:.2f} cents",
        f"- At that point, Vibe correction relative to raw: {vibe_move[peak]:.2f} cents",
        "",
        "Interpretation: a difference while the committed MIDI target is unchanged is a continuous correction/renderer contour issue, not evidence to make the target selector switch earlier.",
    ]
    (args.output / "pitch-window-report.md").write_text("\n".join(report) + "\n")
    print((args.output / "pitch-window-report.md").as_posix())


if __name__ == "__main__":
    main()
