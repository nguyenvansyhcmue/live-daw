#!/usr/bin/env python3
"""Measure each one-knob Artist bounce against case 0 on the same host clock.

This describes audible output differences; it does not identify proprietary
internal algorithms. Run offline against an existing calibration-report.csv.
"""

import argparse
import csv
import math
import sys
from pathlib import Path

import numpy as np

PITCH_TOOL = (Path(__file__).resolve().parent / "artifacts" /
              "crossing24-bounded-preview-20261017-113218" / "source" / "tools")
sys.path.insert(0, str(PITCH_TOOL))
from compare_pitch_correction_bounces import pitch_track, read_mono  # noqa: E402


def rms(signal):
    return math.sqrt(float(np.mean(signal * signal)))


def evaluate(baseline, candidate, rate, baseline_pitch):
    length = min(len(baseline), len(candidate))
    candidate_pitch = pitch_track(candidate[:length], rate)
    reference_pitch = baseline_pitch[:len(candidate_pitch)]
    frames = min(len(reference_pitch), len(candidate_pitch))
    reference_pitch = reference_pitch[:frames]
    candidate_pitch = candidate_pitch[:frames]
    cents = np.full(frames, np.nan)
    valid = (np.isfinite(reference_pitch[:, 1]) & np.isfinite(candidate_pitch[:, 1])
             & (reference_pitch[:, 2] >= 0.55) & (candidate_pitch[:, 2] >= 0.55))
    cents[valid] = 1200.0 * np.log2(candidate_pitch[valid, 1] / reference_pitch[valid, 1])
    voiced = np.abs(cents[valid])
    times = reference_pitch[:, 0] / rate
    phrase = np.abs(cents[valid & (times >= 4.7) & (times <= 5.1)])
    first = np.abs(cents[valid & (times >= 0.0) & (times <= 2.0)])
    def median(values):
        return float(np.median(values)) if len(values) else math.nan
    def p90(values):
        return float(np.quantile(values, 0.9)) if len(values) else math.nan
    level = 20.0 * math.log10(max(rms(candidate[:length]), 1e-12)
                              / max(rms(baseline[:length]), 1e-12))
    return [int(valid.sum()), median(voiced), p90(voiced), median(phrase),
            p90(phrase), median(first), level]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path, help="Artist calibration-report.csv")
    parser.add_argument("output", type=Path, help="destination CSV")
    parser.add_argument("--baseline-case", default="0", help="case number used as reference")
    arguments = parser.parse_args()
    with arguments.report.open(newline="") as handle:
        cases = list(csv.DictReader(handle))
    baseline_case = next((case for case in cases if case["case"] == arguments.baseline_case), None)
    if baseline_case is None:
        raise RuntimeError(f"baseline case {arguments.baseline_case} not found")
    rate, baseline = read_mono(Path(baseline_case["output"]))
    baseline_pitch = pitch_track(baseline, rate)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case", "retune_ms", "flex_tune", "humanize", "natural_vibrato",
                         "paired_voiced_frames", "pitch_abs_median_cents_vs_baseline",
                         "pitch_abs_p90_cents_vs_baseline", "phrase_4p7_5p1_median_cents_vs_baseline",
                         "phrase_4p7_5p1_p90_cents_vs_baseline", "first_2s_median_cents_vs_baseline",
                         "rms_db_vs_baseline"])
        for case in cases:
            candidate_rate, candidate = read_mono(Path(case["output"]))
            if candidate_rate != rate:
                raise RuntimeError(f"sample-rate mismatch in case {case['case']}")
            metrics = evaluate(baseline, candidate, rate, baseline_pitch)
            writer.writerow([case[field] for field in
                             ("case", "retune_ms", "flex_tune", "humanize", "natural_vibrato")]
                            + metrics)
            print(f"measured case {case['case']}: median pitch change {metrics[1]:.2f} cents",
                  flush=True)
    print(f"COMPLETE: {arguments.output}")


if __name__ == "__main__":
    main()
