#!/usr/bin/env python3
"""Locate Artist/Vibe hard-tune-zero divergence in manually tagged technique windows."""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(os.environ.get("PITCH_TOOLS", "/Users/hiimdrdey/autotune/artifacts/crossing24-bounded-preview-20261017-113341/source/tools"))
sys.path.insert(0, str(TOOLS))
from compare_pitch_correction_bounces import cents, pitch_track, read_mono
from measure_artist_vibe_latency_aligned import envelope_delay

CONTROLS = ("retune_ms", "flex_tune", "humanize", "natural_vibrato")


def zero_output(report: Path) -> Path:
    with report.open(newline="") as source:
        for row in csv.DictReader(source):
            if all(abs(float(row[field])) < 1e-9 for field in CONTROLS):
                return Path(row["output"])
    raise ValueError(f"Missing hard-tune-zero case: {report}")


def tagged_intervals(annotation: Path, technique: str) -> list[tuple[float, float]]:
    intervals = []
    for word in json.loads(annotation.read_text(encoding="utf-8")):
        for start, end, flag in zip(word.get("ph_start", []), word.get("ph_end", []), word.get(technique.lower(), [])):
            if str(flag) == "1" and float(end) > float(start):
                intervals.append((float(start), float(end)))
    intervals.sort()
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]: merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else: merged.append((start, end))
    return merged


def in_intervals(times: np.ndarray, intervals: list[tuple[float, float]]) -> np.ndarray:
    return np.array([any(start <= time <= end for start, end in intervals) for time in times], dtype=bool)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--artist-run", type=Path,
                        help="Optional completed run containing the Artist bounces. "
                             "Use this for explicit-VST3 candidate runs that render only Vibe.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    entries = {(entry["technique"], entry["song"], entry["clip"], entry["group"]): entry for entry in plan["entries"]}
    index = list(csv.DictReader((args.run_root / "run-index.csv").open(newline="")))
    rows = []
    for item in index:
        if item["group"] == "Control_Group":
            continue
        entry = entries[(item["technique"], item["song"], item["clip"], item["group"])]
        raw_path = Path(entry["input_wav"])
        annotation = raw_path.with_suffix(".json")
        intervals = tagged_intervals(annotation, item["technique"])
        if not intervals:
            raise ValueError(f"No positive {item['technique']} intervals: {annotation}")
        root = Path(item["comparison"]).parent.parent
        artist_root = ((args.artist_run / root.name) if args.artist_run else root)
        artist_path = zero_output(artist_root / "artist" / "calibration-report.csv")
        vibe_path = zero_output(root / "vibe" / "calibration-report.csv")
        rate, raw = read_mono(raw_path)
        artist_rate, artist = read_mono(artist_path); vibe_rate, vibe = read_mono(vibe_path)
        if rate != artist_rate or rate != vibe_rate: raise ValueError("sample-rate mismatch")
        artist_delay, vibe_delay = envelope_delay(raw, artist, rate), envelope_delay(raw, vibe, rate)
        a, v = pitch_track(artist, rate), pitch_track(vibe, rate)
        a_valid = np.isfinite(a[:, 1]) & (a[:, 2] >= .55)
        v_valid = np.isfinite(v[:, 1]) & (v[:, 2] >= .55)
        times = a[a_valid, 0] / rate - artist_delay / rate
        v_times = v[v_valid, 0] / rate - vibe_delay / rate
        if len(v_times) < 2:
            raise ValueError(f"Insufficient reliable Vibe pitch frames: {vibe_path}")
        interpolated = np.interp(times, v_times, v[v_valid, 1], left=np.nan, right=np.nan)
        artist_hz = a[a_valid, 1]
        # Do not fabricate pitch by interpolating across unvoiced/low-confidence
        # gaps. Only interpolate between adjacent 64-sample analysis frames.
        right = np.searchsorted(v_times, times, side="left")
        bounded = (right > 0) & (right < len(v_times))
        adjacent = np.zeros(times.shape, dtype=bool)
        positions = np.flatnonzero(bounded)
        adjacent[positions] = (v_times[right[positions]] - v_times[right[positions] - 1]) <= (64.1 / rate)
        usable = np.isfinite(interpolated) & (artist_hz > 0) & (interpolated > 0) & adjacent
        times, error = times[usable], np.abs(cents(interpolated[usable], artist_hz[usable]))
        tagged = in_intervals(times, intervals)
        if not tagged.any() or (~tagged).sum() == 0: raise ValueError(f"Insufficient tagged/un-tagged frames: {annotation}")
        rows.append({"technique": item["technique"], "song": item["song"], "clip": item["clip"], "tagged_seconds": round(sum(end-start for start, end in intervals), 3), "tagged_frames": int(tagged.sum()), "all_median_abs_cents": float(np.median(error)), "tagged_median_abs_cents": float(np.median(error[tagged])), "outside_median_abs_cents": float(np.median(error[~tagged])), "tagged_p90_abs_cents": float(np.quantile(error[tagged], .90)), "artist_latency_samples": artist_delay, "vibe_latency_samples": vibe_delay})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
