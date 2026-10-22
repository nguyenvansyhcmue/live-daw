#!/usr/bin/env python3
"""Explain whether a correction-transfer deficit is steady-state or transition-only.

Consumes the optional aligned transfer-frame debug CSV and the fitted transition
table. It never touches DSP source or plugin bundles.
"""
import argparse
import csv
import math
from pathlib import Path


def median(values):
    values = sorted(values)
    if not values:
        return math.nan
    centre = len(values) // 2
    return values[centre] if len(values) % 2 else (values[centre - 1] + values[centre]) / 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("frames", type=Path)
    parser.add_argument("transitions", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--window-ms", type=float, default=40.0,
                        help="half-width around fitted Artist transition, default 40 ms")
    args = parser.parse_args()

    events = []
    with args.transitions.open(newline="") as handle:
        for row in csv.DictReader(handle):
            events.append({
                "time": float(row["time_seconds"]),
                "direction": row["direction"],
                "artist_step": float(row["artist_step_cents"]),
                "vibe_step": float(row["vibe_step_cents"]),
                "t50_delta": float(row["vibe_minus_artist_t50_ms"]),
            })

    frames = []
    with args.frames.open(newline="") as handle:
        for row in csv.DictReader(handle):
            artist = float(row["artist_movement_cents"])
            vibe = float(row["vibe_movement_cents"])
            frames.append({
                "time": float(row["raw_time_seconds"]),
                "artist": artist,
                "vibe": vibe,
                "error": float(row["vibe_minus_artist_cents"]),
            })

    half_window = args.window_ms / 1000.0
    fit = [f for f in frames if 15 <= abs(f["artist"]) <= 400]
    transition = [f for f in fit if any(abs(f["time"] - e["time"]) <= half_window for e in events)]
    steady = [f for f in fit if not any(abs(f["time"] - e["time"]) <= half_window for e in events)]
    def describe(group):
        errors = [f["error"] for f in group]
        return len(group), median(errors), median([abs(v) for v in errors])

    rows = []
    for event in events:
        nearby = [f for f in frames if abs(f["time"] - event["time"]) <= half_window]
        if not nearby:
            continue
        worst = max(nearby, key=lambda f: abs(f["error"]))
        rows.append((abs(worst["error"]), event, worst, nearby))
    rows.sort(reverse=True, key=lambda row: row[0])

    fit_count, fit_signed, fit_abs = describe(fit)
    tr_count, tr_signed, tr_abs = describe(transition)
    steady_count, steady_signed, steady_abs = describe(steady)
    report = [
        "# Hook-2 transition versus steady-transfer diagnosis",
        "",
        f"- Fitted movement frames: {fit_count}",
        f"- Transition windows: ±{args.window_ms:.0f} ms around {len(events)} fitted Artist events", 
        "",
        "| Region | Frames | Vibe − Artist median | median absolute error |",
        "|---|---:|---:|---:|",
        f"| All fit frames | {fit_count} | {fit_signed:.2f} cents | {fit_abs:.2f} cents |",
        f"| Around transitions | {tr_count} | {tr_signed:.2f} cents | {tr_abs:.2f} cents |",
        f"| Steady portions | {steady_count} | {steady_signed:.2f} cents | {steady_abs:.2f} cents |",
        "",
        "## Largest transition-bound windows",
        "",
        "| Artist event | Direction | Artist step | Vibe step | Vibe–Artist t50 | Worst frame time | Worst error |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for _, event, worst, _ in rows[:16]:
        report.append(
            f"| {event['time']:.3f}s | {event['direction']} | {event['artist_step']:.1f} | "
            f"{event['vibe_step']:.1f} | {event['t50_delta']:.1f} ms | {worst['time']:.3f}s | {worst['error']:.1f} cents |"
        )
    report.extend([
        "",
        "## Interpretation",
        "",
        "If transition windows are much worse than steady portions, do not tune global delivery gain: "
        "it will alter held notes while the actual defect remains an analysis/control-to-OLA handoff. "
        "The next candidate must be a bounded handoff/trajectory timing experiment and must retain the same Key/Scale and selector policy.",
        "",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(report))
    print(args.output)


if __name__ == "__main__":
    main()
