#!/usr/bin/env python3
"""Measure the correction-transfer curve of two Hook-2 renders.

This intentionally compares *pitch movement relative to the same raw vocal*,
after each render is independently latency aligned.  It is therefore useful
for deciding whether a renderer needs a gain/curve adjustment, rather than
mistaking a fixed plugin latency or renderer phase for a pitch error.
"""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


def load_report(path):
    with path.open(newline="") as handle:
        return {int(row["case"]): row for row in csv.DictReader(handle)}


def interpolate(times, values, query):
    valid = np.isfinite(values)
    if valid.sum() < 2:
        return np.full(query.shape, np.nan)
    return np.interp(query, times[valid], values[valid], left=np.nan, right=np.nan)


def robust_slope(x, y):
    # A through-origin slope expresses how much Vibe moves for a given Artist
    # movement.  Keep the analysis in the musical, non-octave-error region.
    keep = np.isfinite(x) & np.isfinite(y) & (np.abs(x) >= 15.0) & (np.abs(x) <= 400.0) & (np.abs(y) <= 500.0)
    if keep.sum() < 8:
        return np.nan, 0
    x, y = x[keep], y[keep]
    return float(np.dot(x, y) / max(np.dot(x, x), 1.0e-12)), int(keep.sum())


def safe_stat(values, function):
    return float(function(values)) if values.size else np.nan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("artist_report", type=Path)
    parser.add_argument("vibe_report", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pitch-tools", type=Path, required=True,
                        help="directory containing compare_pitch_correction_bounces.py")
    parser.add_argument("--write-frame-debug", action="store_true",
                        help="write latency-aligned per-frame movement evidence for diagnosis; does not change metrics")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(args.pitch_tools))
    from compare_pitch_correction_bounces import pitch_track, cents
    from measure_artist_vibe_latency_aligned import read_mono, envelope_delay

    artists, vibes = load_report(args.artist_report), load_report(args.vibe_report)
    common_cases = sorted(set(artists).intersection(vibes))
    rate, raw = read_mono(args.raw)
    raw_track = pitch_track(raw, rate)
    raw_times = raw_track[:, 0] / rate
    raw_valid = np.isfinite(raw_track[:, 1]) & (raw_track[:, 2] >= 0.55)

    bins = [(0, 10), (10, 25), (25, 50), (50, 100), (100, 200), (200, 400), (400, np.inf)]
    all_rows, all_artist, all_vibe = [], [], []
    debug_rows = []

    for case in common_cases:
        artist_path, vibe_path = Path(artists[case]["output"]), Path(vibes[case]["output"])
        artist_rate, artist = read_mono(artist_path)
        vibe_rate, vibe = read_mono(vibe_path)
        if artist_rate != rate or vibe_rate != rate:
            raise RuntimeError(f"sample-rate mismatch in case {case}")

        artist_delay = envelope_delay(raw, artist, rate)
        vibe_delay = envelope_delay(raw, vibe, rate)
        artist_track, vibe_track = pitch_track(artist, rate), pitch_track(vibe, rate)
        artist_times = artist_track[:, 0] / rate - artist_delay / rate
        vibe_times = vibe_track[:, 0] / rate - vibe_delay / rate
        artist_f0 = interpolate(artist_times, artist_track[:, 1], raw_times)
        vibe_f0 = interpolate(vibe_times, vibe_track[:, 1], raw_times)
        artist_conf = interpolate(artist_times, artist_track[:, 2], raw_times)
        vibe_conf = interpolate(vibe_times, vibe_track[:, 2], raw_times)
        usable = raw_valid & np.isfinite(artist_f0) & np.isfinite(vibe_f0) \
            & (artist_conf >= 0.55) & (vibe_conf >= 0.55) \
            & (raw_track[:, 1] > 0) & (artist_f0 > 0) & (vibe_f0 > 0)
        artist_move = cents(artist_f0[usable], raw_track[usable, 1])
        vibe_move = cents(vibe_f0[usable], raw_track[usable, 1])
        error = vibe_move - artist_move
        if args.write_frame_debug:
            usable_indices = np.flatnonzero(usable)
            for index, artist_cents, vibe_cents, delta_cents in zip(usable_indices, artist_move, vibe_move, error):
                debug_rows.append({
                    "case": case,
                    "raw_time_seconds": float(raw_times[index]),
                    "raw_hz": float(raw_track[index, 1]),
                    "artist_hz": float(artist_f0[index]),
                    "vibe_hz": float(vibe_f0[index]),
                    "artist_movement_cents": float(artist_cents),
                    "vibe_movement_cents": float(vibe_cents),
                    "vibe_minus_artist_cents": float(delta_cents),
                })
        slope, fit_frames = robust_slope(artist_move, vibe_move)
        row = {
            "case": case,
            "retune_ms": artists[case]["retune_ms"],
            "flex_tune": artists[case]["flex_tune"],
            "humanize": artists[case]["humanize"],
            "natural_vibrato": artists[case]["natural_vibrato"],
            "artist_delay_samples": artist_delay,
            "vibe_delay_samples": vibe_delay,
            "usable_frames": int(usable.sum()),
            "fit_frames": fit_frames,
            "transfer_slope_vibe_per_artist": slope,
            "signed_move_error_median_cents": safe_stat(error, np.median),
            "absolute_move_error_median_cents": safe_stat(np.abs(error), np.median),
            "absolute_move_error_p90_cents": safe_stat(np.abs(error), lambda x: np.quantile(x, .90)),
        }
        for low, high in bins:
            bin_error = error[(np.abs(artist_move) >= low) & (np.abs(artist_move) < high)]
            label = f"{low:g}_{'plus' if not np.isfinite(high) else f'{high:g}'}"
            row[f"bin_{label}_frames"] = int(bin_error.size)
            row[f"bin_{label}_signed_median"] = safe_stat(bin_error, np.median)
            row[f"bin_{label}_absolute_median"] = safe_stat(np.abs(bin_error), np.median)
        all_rows.append(row)
        all_artist.append(artist_move)
        all_vibe.append(vibe_move)

    fieldnames = list(all_rows[0]) if all_rows else []
    with (args.output / "transfer-summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    if args.write_frame_debug:
        with (args.output / "transfer-frame-debug.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "case", "raw_time_seconds", "raw_hz", "artist_hz", "vibe_hz",
                "artist_movement_cents", "vibe_movement_cents", "vibe_minus_artist_cents",
            ])
            writer.writeheader()
            writer.writerows(debug_rows)

    artist_move, vibe_move = np.concatenate(all_artist), np.concatenate(all_vibe)
    error = vibe_move - artist_move
    global_slope, global_fit_frames = robust_slope(artist_move, vibe_move)
    with (args.output / "transfer-bins.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["artist_correction_abs_bin_cents", "frames", "vibe_minus_artist_signed_median_cents", "absolute_median_cents"])
        for low, high in bins:
            selected = error[(np.abs(artist_move) >= low) & (np.abs(artist_move) < high)]
            title = f"{low:g}+" if not np.isfinite(high) else f"{low:g}-{high:g}"
            writer.writerow([title, selected.size, safe_stat(selected, np.median), safe_stat(np.abs(selected), np.median)])

    ordered = sorted(all_rows, key=lambda row: row["absolute_move_error_median_cents"])
    report = [
        "# Hook-2 correction-transfer analysis",
        "",
        "Each bounce is aligned independently to the raw vocal before measuring pitch movement. "
        "A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; "
        "this does not compare waveform phase or fixed latency.",
        "",
        f"- Shared configurations: {len(all_rows)}",
        f"- Reliable voiced frames: {error.size}",
        f"- Global correction-transfer slope: {global_slope:.4f} ({global_fit_frames} fit frames)",
        f"- Global median absolute movement error: {np.median(np.abs(error)):.2f} cents",
        "",
        "| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |",
        "|---:|---|---:|---:|---:|",
    ]
    for row in ordered:
        report.append("| {case} | {retune_ms}/{flex_tune}/{humanize}/{natural_vibrato} | "
                      "{transfer_slope_vibe_per_artist:.4f} | {absolute_move_error_median_cents:.2f} | "
                      "{absolute_move_error_p90_cents:.2f} |".format(**row))
    report.extend(["", "## By Artist correction magnitude", "", "| Artist movement | Frames | Vibe − Artist median | median absolute error |", "|---|---:|---:|---:|"])
    for low, high in bins:
        selected = error[(np.abs(artist_move) >= low) & (np.abs(artist_move) < high)]
        title = f"{low:g}+" if not np.isfinite(high) else f"{low:g}-{high:g}"
        report.append(f"| {title} cents | {selected.size} | {safe_stat(selected, np.median):.2f} | {safe_stat(np.abs(selected), np.median):.2f} |")
    (args.output / "transfer-report.md").write_text("\n".join(report) + "\n")
    print((args.output / "transfer-report.md").as_posix())


if __name__ == "__main__":
    main()
