#!/usr/bin/env python3
"""Measure whether a Vibe renderer follows its delivered correction control.

This is intentionally diagnostic-only.  It aligns the rendered signal to the
raw input, then compares audible pitch correction with the control cents that
were handed to the renderer.  It separates a selector mistake from a renderer
transfer/OLA mistake without changing a single DSP parameter.
"""
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
    parser.add_argument("render", type=Path)
    parser.add_argument("intervals", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pitch-tools", type=Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.pitch_tools))
    from compare_pitch_correction_bounces import pitch_track
    from measure_artist_vibe_latency_aligned import envelope_delay, read_mono

    rate, raw = read_mono(args.raw)
    render_rate, rendered = read_mono(args.render)
    if rate != render_rate:
        raise SystemExit("sample-rate mismatch")

    raw_track = pitch_track(raw, rate)
    rendered_track = pitch_track(rendered, rate)
    raw_time = raw_track[:, 0] / rate
    delay = envelope_delay(raw, rendered, rate)
    rendered_time = rendered_track[:, 0] / rate - delay / rate
    valid_render = np.isfinite(rendered_track[:, 1]) & (rendered_track[:, 2] >= .55)
    valid_raw = np.isfinite(raw_track[:, 1]) & (raw_track[:, 2] >= .55)

    rows: list[dict[str, str]] = []
    with args.intervals.open(newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                if not (np.isfinite(float(row["rawF0"])) and float(row["rawF0"]) > 0.0):
                    continue
                # Do not score startup, dry safety, or detector-loss rows.
                # Those intentionally carry a zero control and are not a
                # renderer transfer measurement.
                if int(row["committedTargetMidi"]) < 0 or int(row["correctionIsActive"]) == 0:
                    continue
                if int(row["sourceControlValid"]) == 0 or int(row["rendererShouldRenderWet"]) == 0:
                    continue
                delivered = float(row["deliveredRendererCorrectionCents"])
                input_control = float(row["rendererInputCorrectionCents"])
                timestamp = float(row["timeMs"]) / 1000.0
            except (KeyError, ValueError):
                continue
            if not np.isfinite(delivered):
                continue
            actual_hz = np.interp(timestamp, rendered_time[valid_render], rendered_track[valid_render, 1], left=np.nan, right=np.nan)
            if not np.isfinite(actual_hz) or actual_hz <= 0.0:
                continue
            raw_hz = float(row["rawF0"])
            audible = float(cents(np.asarray([actual_hz]), np.asarray([raw_hz]))[0])
            rows.append({
                "time_seconds": f"{timestamp:.6f}",
                "target_midi": row["committedTargetMidi"],
                "target_changed": row["targetChanged"],
                "raw_hz": row["rawF0"],
                "delivered_correction_cents": f"{delivered:.6f}",
                "renderer_input_correction_cents": f"{input_control:.6f}",
                "audible_correction_cents": f"{audible:.6f}",
                "audible_minus_delivered_cents": f"{audible - delivered:.6f}",
                "ola_target_midi": row.get("olaDominantGrainTargetMidi", ""),
                "ola_ratio": row.get("olaDominantGrainRatio", ""),
            })

    if not rows:
        raise SystemExit("no jointly reliable control/pitch rows")

    # An envelope latency aligns the files globally, but a PSOLA grain can
    # make the audible pitch follow the control several milliseconds later.
    # Estimate that *extra* response lag before judging renderer transfer.
    # Out-of-range octave tracker frames are excluded from this estimator.
    times = np.asarray([float(row["time_seconds"]) for row in rows])
    controls = np.asarray([float(row["delivered_correction_cents"]) for row in rows])

    def audible_correction(query: np.ndarray) -> np.ndarray:
        raw_hz = np.interp(query, raw_time[valid_raw], raw_track[valid_raw, 1], left=np.nan, right=np.nan)
        output_hz = np.interp(query, rendered_time[valid_render], rendered_track[valid_render, 1], left=np.nan, right=np.nan)
        values = np.full(query.shape, np.nan)
        ok = np.isfinite(raw_hz) & np.isfinite(output_hz) & (raw_hz > 0.0) & (output_hz > 0.0)
        values[ok] = cents(output_hz[ok], raw_hz[ok])
        return values

    baseline_audible = audible_correction(times)
    baseline_valid = np.isfinite(baseline_audible) & (np.abs(baseline_audible) <= 400.0) & (np.abs(controls) <= 200.0)
    if baseline_valid.sum() < 100:
        raise SystemExit("insufficient non-octave control/pitch rows")
    lag_candidates = np.linspace(-0.080, 0.080, 241)
    lag_scores = []
    for lag in lag_candidates:
        candidate = audible_correction(times + lag)
        usable = baseline_valid & np.isfinite(candidate) & (np.abs(candidate) <= 400.0)
        lag_scores.append(np.median(np.abs(candidate[usable] - controls[usable])) if usable.sum() >= 100 else np.inf)
    best_index = int(np.argmin(lag_scores))
    best_lag = float(lag_candidates[best_index])
    best_audible = audible_correction(times + best_lag)
    for row, audible in zip(rows, best_audible):
        row["audible_correction_best_aligned_cents"] = f"{audible:.6f}"
        row["audible_minus_delivered_best_aligned_cents"] = f"{audible - float(row['delivered_correction_cents']):.6f}"
    error = np.asarray([
        abs(float(row["audible_minus_delivered_best_aligned_cents"]))
        for row in rows
        if np.isfinite(float(row["audible_correction_best_aligned_cents"]))
        and abs(float(row["audible_correction_best_aligned_cents"])) <= 400.0
    ])
    args.output.mkdir(parents=True, exist_ok=True)
    output_csv = args.output / "renderer-control-transfer.csv"
    with output_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    notable = sorted(
        (row for row in rows if np.isfinite(float(row["audible_correction_best_aligned_cents"]))
         and abs(float(row["audible_correction_best_aligned_cents"])) <= 400.0),
        key=lambda row: abs(float(row["audible_minus_delivered_best_aligned_cents"])), reverse=True)[:12]
    report = [
        "# Renderer control-transfer report", "",
        f"- Render latency vs raw: {delay} samples ({delay / rate * 1000.0:.2f} ms)",
        f"- Best extra renderer response lag: {best_lag * 1000.0:.2f} ms",
        f"- Comparable control/pitch points: {len(rows)}",
        f"- Median |audible − delivered| after lag alignment: {np.median(error):.2f} cents",
        f"- P90 |audible − delivered| after lag alignment: {np.quantile(error, .90):.2f} cents", "",
        "## Largest control-to-audible residuals", "",
        "| Raw time | Target | Delivered ct | Audible ct | Residual ct | OLA target |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in notable:
        report.append("| {time_seconds} | {target_midi} | {delivered_correction_cents} | {audible_correction_best_aligned_cents} | {audible_minus_delivered_best_aligned_cents} | {ola_target_midi} |".format(**row))
    (args.output / "renderer-control-transfer.md").write_text("\n".join(report) + "\n")
    print((args.output / "renderer-control-transfer.md").as_posix())


if __name__ == "__main__":
    main()
