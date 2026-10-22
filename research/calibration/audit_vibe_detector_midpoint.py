#!/usr/bin/env python3
"""Compare Vibe's traced raw F0 with an independent raw-audio F0 reference."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


def midi(hz: np.ndarray) -> np.ndarray:
    return 69.0 + 12.0 * np.log2(hz / 440.0)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("raw", type=Path)
    p.add_argument("intervals", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--pitch-tools", type=Path, required=True)
    p.add_argument("--start", type=float, default=3.50)
    p.add_argument("--end", type=float, default=3.90)
    p.add_argument("--midpoint-midi", type=float, default=58.0)
    p.add_argument("--vibe-frame-samples", type=int, default=1024,
                   help="Vibe analysis-frame length. Trace timestamps are frame-end timestamps.")
    args = p.parse_args()
    sys.path.insert(0, str(args.pitch_tools))
    from compare_pitch_correction_bounces import pitch_track
    from measure_artist_vibe_latency_aligned import read_mono

    rate, audio = read_mono(args.raw)
    if args.vibe_frame_samples <= 0:
        raise SystemExit("--vibe-frame-samples must be positive")
    reference = pitch_track(audio, rate)
    valid = np.isfinite(reference[:, 1]) & (reference[:, 2] >= .55)
    ref_time = reference[valid, 0] / rate
    ref_midi = midi(reference[valid, 1])
    rows = []
    with args.intervals.open(newline="") as handle:
        for row in csv.DictReader(handle):
            t = float(row["timeMs"]) / 1000.0
            hz = float(row["rawF0"])
            if not (args.start <= t <= args.end and np.isfinite(hz) and hz > 0.0):
                continue
            vibe_midi = float(midi(np.asarray([hz]))[0])
            reference_midi = float(np.interp(t, ref_time, ref_midi, left=np.nan, right=np.nan))
            rows.append({
                "time_seconds": f"{t:.6f}",
                "vibe_raw_hz": f"{hz:.6f}",
                "vibe_raw_midi": f"{vibe_midi:.6f}",
                "reference_raw_midi": f"{reference_midi:.6f}",
                "vibe_minus_reference_cents": f"{(vibe_midi - reference_midi) * 100.0:.6f}",
                "vibe_target_midi": row["committedTargetMidi"],
            })
    if not rows:
        raise SystemExit("no comparable F0 rows")
    def upward_crossings(key: str) -> list[float]:
        """Only count a below-to-at/above midpoint transition.

        The analysis window can begin while a note is already above the
        midpoint.  Treating its first sample as a crossing hid the actual
        return transition being audited.
        """
        values = np.asarray([float(row[key]) for row in rows])
        times = np.asarray([float(row["time_seconds"]) for row in rows])
        return times[1:][(values[1:] >= args.midpoint_midi)
                         & (values[:-1] < args.midpoint_midi)].tolist()

    vibe_upward = upward_crossings("vibe_raw_midi")
    ref_upward = upward_crossings("reference_raw_midi")
    # Pair the reference event with the first Vibe event at/after it. This
    # preserves causal ordering for a detector-onset diagnostic.
    ref_cross = ref_upward[-1] if ref_upward else None
    vibe_cross = (next((t for t in vibe_upward if ref_cross is None or t >= ref_cross), None)
                  if vibe_upward else None)
    # The external reference labels an estimate at the *centre* of its
    # analysis window. Vibe's diagnostic row is emitted at the end of its
    # input window. Keep both timings: publication time is what the live
    # engine can act on; centre time is the fair detector-estimate comparison.
    vibe_centre_cross = (vibe_cross - 0.5 * args.vibe_frame_samples / rate
                         if vibe_cross is not None else None)
    delta = np.asarray([abs(float(row["vibe_minus_reference_cents"])) for row in rows])
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "detector-midpoint.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    report = [
        "# Vibe detector midpoint audit", "",
        f"- Window: {args.start:.3f}–{args.end:.3f} s; midpoint: MIDI {args.midpoint_midi:.2f}",
        f"- Vibe analysis frame: {args.vibe_frame_samples} samples ({args.vibe_frame_samples / rate * 1000.0:.2f} ms); trace time is frame end",
        f"- Vibe upward midpoint crossings: {', '.join(f'{t:.6f}' for t in vibe_upward) or 'none'} s",
        f"- Independent upward midpoint crossings: {', '.join(f'{t:.6f}' for t in ref_upward) or 'none'} s",
        f"- Paired Vibe raw-F0 crossing: {'none' if vibe_cross is None else f'{vibe_cross:.6f} s'}",
        f"- Paired Vibe raw-F0 crossing, frame-centre aligned: {'none' if vibe_centre_cross is None else f'{vibe_centre_cross:.6f} s'}",
        f"- Paired independent raw-F0 crossing: {'none' if ref_cross is None else f'{ref_cross:.6f} s'}",
        f"- Detector median absolute disagreement: {np.median(delta):.2f} cents",
        f"- Detector P90 absolute disagreement: {np.quantile(delta, .90):.2f} cents",
    ]
    if vibe_cross is not None and ref_cross is not None:
        report.append(f"- Vibe publication minus reference centre: {(vibe_cross - ref_cross) * 1000.0:.2f} ms")
        report.append(f"- Vibe detector centre minus reference centre: {(vibe_centre_cross - ref_cross) * 1000.0:.2f} ms")
    (args.output / "detector-midpoint-report.md").write_text("\n".join(report) + "\n")
    print((args.output / "detector-midpoint-report.md").as_posix())


if __name__ == "__main__":
    main()
