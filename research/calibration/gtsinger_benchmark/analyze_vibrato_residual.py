#!/usr/bin/env python3
"""Measure vibrato depth and timing of an explicit Vibe run versus Artist.

This is a diagnostic, not a tuning rule.  It deliberately analyses only the
all-zero user controls so a difference cannot be blamed on Flex, Humanize or
Natural Vibrato knob settings.
"""
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
            if all(abs(float(row[name])) < 1e-9 for name in CONTROLS):
                return Path(row["output"])
    raise ValueError(f"Missing all-zero row: {report}")


def tagged_intervals(annotation: Path) -> list[tuple[float, float]]:
    windows: list[tuple[float, float]] = []
    for word in json.loads(annotation.read_text(encoding="utf-8")):
        for start, end, active in zip(word.get("ph_start", []), word.get("ph_end", []), word.get("vibrato", [])):
            if str(active) == "1" and float(end) > float(start):
                windows.append((float(start), float(end)))
    return windows


def safe_interp(reference_times: np.ndarray, trace: np.ndarray, delay: int, rate: int) -> tuple[np.ndarray, np.ndarray]:
    valid = np.isfinite(trace[:, 1]) & (trace[:, 2] >= 0.55)
    points = trace[valid]
    times = points[:, 0] / rate - delay / rate
    right = np.searchsorted(times, reference_times)
    usable = (right > 0) & (right < len(times))
    positions = np.flatnonzero(usable)
    usable[positions] &= (times[right[positions]] - times[right[positions] - 1]) <= 64.1 / rate
    return np.interp(reference_times, times, points[:, 1], left=np.nan, right=np.nan), usable


def residual_cents(hz: np.ndarray, rate_hz: float) -> np.ndarray:
    values = 1200.0 * np.log2(hz / 440.0)
    # A 300-ms moving mean removes the note centre while retaining normal vocal
    # vibrato.  NaN handling is done before this function is called.
    width = min(len(values), max(3, int(round(0.300 * rate_hz))))
    if width % 2 == 0:
        width += 1
    if width > len(values):
        width -= 2
    trend = np.convolve(values, np.ones(width) / width, mode="same")
    return values - trend


def best_lag_ms(artist: np.ndarray, vibe: np.ndarray, hop_seconds: float) -> tuple[float, float]:
    best = (-np.inf, 0)
    maximum = int(round(0.120 / hop_seconds))
    for lag in range(-maximum, maximum + 1):
        if lag < 0:
            a, v = artist[-lag:], vibe[:lag]
        elif lag > 0:
            a, v = artist[:-lag], vibe[lag:]
        else:
            a, v = artist, vibe
        if len(a) < 12 or np.std(a) < 1e-6 or np.std(v) < 1e-6:
            continue
        correlation = float(np.corrcoef(a, v)[0, 1])
        if correlation > best[0]:
            best = (correlation, lag)
    return best[1] * hop_seconds * 1000.0, best[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vibe_run", type=Path)
    parser.add_argument("artist_run", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    entries = {(e.get("dataset_voice", ""), e["technique"], e["song"], e["clip"], e["group"]): e for e in plan["entries"]}
    rows = []
    with (args.vibe_run / "run-index.csv").open(newline="") as source:
        jobs = list(csv.DictReader(source))
    for job in jobs:
        if job["technique"] != "Vibrato" or job["group"] != "Vibrato_Group":
            continue
        key = (job.get("dataset_voice", ""), job["technique"], job["song"], job["clip"], job["group"])
        entry = entries[key]
        raw_path = Path(entry["input_wav"])
        name = Path(job["comparison"]).parent.parent.name
        vibe_path = zero_output(Path(job["comparison"]).parent.parent / "vibe" / "calibration-report.csv")
        artist_path = zero_output(args.artist_run / name / "artist" / "calibration-report.csv")
        rate, raw = read_mono(raw_path)
        ar, artist = read_mono(artist_path)
        vr, vibe = read_mono(vibe_path)
        if ar != rate or vr != rate:
            raise ValueError(f"Sample-rate mismatch: {name}")
        artist_delay = envelope_delay(raw, artist, rate)
        vibe_delay = envelope_delay(raw, vibe, rate)
        atrace = pitch_track(artist, rate)
        valid = np.isfinite(atrace[:, 1]) & (atrace[:, 2] >= 0.55)
        atimes = atrace[valid, 0] / rate - artist_delay / rate
        ahz = atrace[valid, 1]
        vtrace = pitch_track(vibe, rate)
        vhz, usable = safe_interp(atimes, vtrace, vibe_delay, rate)
        tagged = np.array([any(start <= t <= end for start, end in tagged_intervals(raw_path.with_suffix('.json'))) for t in atimes])
        usable &= tagged & np.isfinite(vhz) & (ahz > 0) & (vhz > 0)
        if usable.sum() < 24:
            raise ValueError(f"Insufficient reliable tagged frames: {name}")
        # Split into contiguous tagged regions; never calculate a smoother
        # across a phrase break or an unvoiced gap.
        indices = np.flatnonzero(usable)
        pieces = np.split(indices, np.flatnonzero(np.diff(indices) > 1) + 1)
        artist_residual, vibe_residual, error = [], [], []
        for piece in pieces:
            if len(piece) < 24:
                continue
            a = residual_cents(ahz[piece], rate / 64.0)
            v = residual_cents(vhz[piece], rate / 64.0)
            artist_residual.extend(a); vibe_residual.extend(v)
            error.extend(np.abs(cents(vhz[piece], ahz[piece])))
        a = np.asarray(artist_residual); v = np.asarray(vibe_residual)
        if len(a) < 24:
            raise ValueError(f"No contiguous vibrato region: {name}")
        lag, correlation = best_lag_ms(a, v, 64.0 / rate)
        rows.append({
            "dataset_voice": job["dataset_voice"], "song": job["song"], "clip": job["clip"],
            "frames": len(a), "artist_vibrato_std_cents": float(np.std(a)),
            "vibe_vibrato_std_cents": float(np.std(v)),
            "depth_ratio_vibe_over_artist": float(np.std(v) / max(np.std(a), 1e-9)),
            "best_lag_ms_vibe_relative_artist": lag, "residual_correlation": correlation,
            "tagged_median_abs_error_cents": float(np.median(error)),
            "tagged_p90_abs_error_cents": float(np.quantile(error, 0.90)),
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
