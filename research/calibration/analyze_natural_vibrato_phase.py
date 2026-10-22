#!/usr/bin/env python3
"""Score Natural Vibrato candidates by residual-F0 phase, not median F0."""
import csv
import sys
from pathlib import Path

import numpy as np


def rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def value(row, field):
    # The runner prints either `10` or `10.0` depending on the report stage.
    # Canonicalise numerically before using metadata as a join key.
    return float(row[field])


def key(row):
    return tuple(value(row, field) for field in
                 ("retune_ms", "flex_tune", "humanize", "natural_vibrato"))


def trace(path):
    data = np.genfromtxt(path, delimiter=",", names=True)
    return data["time_seconds"], data["midi_note"]


def residual(values, width=151):
    # Remove slow note drift; leave the 4–8 Hz vibrato contour.
    width = min(width if width % 2 else width + 1, max(3, len(values) // 3 * 2 + 1))
    kernel = np.ones(width) / width
    return values - np.convolve(values, kernel, mode="same")


def phase_metrics(artist, vibe, max_lag_frames=96):
    a = residual(artist); v = residual(vibe)
    best = (-np.inf, 0)
    for lag in range(-max_lag_frames, max_lag_frames + 1):
        aa, vv = (a[lag:], v[:-lag]) if lag > 0 else ((a[:lag], v[-lag:]) if lag < 0 else (a, v))
        if len(aa) < 128: continue
        denom = np.linalg.norm(aa) * np.linalg.norm(vv)
        corr = float(np.dot(aa, vv) / denom) if denom else -np.inf
        if corr > best[0]: best = (corr, lag)
    return best


def segment_correlations(artist, vibe, frames=3000):
    """Independent ~4 s checks; rejects an apparent winner driven by one phrase."""
    edge = 151  # omit moving-average boundary artefacts
    artist, vibe = artist[edge:-edge], vibe[edge:-edge]
    scores = []
    for start in range(0, len(artist) - frames + 1, frames):
        a, v = artist[start:start + frames], vibe[start:start + frames]
        denom = np.linalg.norm(a) * np.linalg.norm(v)
        if denom:
            scores.append(float(np.dot(a, v) / denom))
    return scores


def main(root_text):
    root = Path(root_text)
    outputs = []
    for candidate in sorted(root.glob("phase-*")):
        # The comparison report defines the exact case-id used by f0-traces.
        # Do not infer it from lexical CSV ordering.
        report = candidate / "comparison" / "calibration-report.csv"
        traces = candidate / "comparison" / "f0-traces"
        if not report.exists() or not traces.exists(): continue
        per_case = []
        segment_scores = []
        for row in rows(report):
            item = key(row)
            if item[0] != 10.0 or item[1] != 0.0 or item[2] != 0.0 or item[3] not in {-12.0, -9.0, -6.0}:
                continue
            number = int(row["case"])
            at, av = trace(traces / f"case-{number}-artist.csv")
            vt, vv = trace(traces / f"case-{number}-vibe.csv")
            lo, hi = max(at[0], vt[0]), min(at[-1], vt[-1])
            grid = np.arange(lo, hi, 64.0 / 48000.0)
            if len(grid) < 256: continue
            aligned_artist = np.interp(grid, at, av)
            aligned_vibe = np.interp(grid, vt, vv)
            corr, lag = phase_metrics(aligned_artist, aligned_vibe)
            lag_ms = lag * 64.0 / 48.0
            per_case.append((item[3], corr, lag_ms))
            segment_scores.extend(segment_correlations(residual(aligned_artist), residual(aligned_vibe)))
        if per_case:
            outputs.append((candidate.name, np.mean([x[1] for x in per_case]),
                            np.mean([abs(x[2]) for x in per_case]), per_case,
                            np.mean(segment_scores), np.std(segment_scores), len(segment_scores)))
    print("candidate,mean_phase_correlation,mean_abs_phase_lag_ms,segment_mean,segment_std,segments,details")
    for name, correlation, lag, details, segment_mean, segment_std, segment_count in outputs:
        detail = "; ".join(f"N{n}:r={c:.4f},lag={l:.2f}ms" for n,c,l in details)
        print(f"{name},{correlation:.6f},{lag:.3f},{segment_mean:.6f},{segment_std:.6f},{segment_count},\"{detail}\"")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: analyze_natural_vibrato_phase.py PHASE_FIT_DIRECTORY")
    main(sys.argv[1])
