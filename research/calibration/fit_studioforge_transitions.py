#!/usr/bin/env python3
"""Extract latency-aligned pitch-transition response metrics from DAW bounces.

This is a measurement tool: it changes neither the DAW nor the plug-in.  It
uses RMS-envelope latency alignment, then compares Artist/Vibe pitch traces on
the raw-input timeline.  The 1024-sample pitch estimator delay is shared by
both traces, so timing *differences* are usable for fitting control laws.
"""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


def load_report(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def case_key(row):
    return tuple(row[name] for name in ("retune_ms", "flex_tune", "humanize", "natural_vibrato"))


def midi(hz):
    return 69.0 + 12.0 * np.log2(hz / 440.0)


def smooth(values, radius=2):
    """Small median smoother; preserves step direction better than a mean."""
    output = values.copy()
    for index in range(len(values)):
        lo, hi = max(0, index - radius), min(len(values), index + radius + 1)
        output[index] = np.nanmedian(values[lo:hi])
    return output


def merge_runs(active, maximum_gap_frames=8):
    starts, runs, start, gap = [], [], None, 0
    for index, value in enumerate(active):
        if value:
            if start is None:
                start, gap = index, 0
            else:
                gap = 0
        elif start is not None:
            gap += 1
            if gap > maximum_gap_frames:
                runs.append((start, index - gap + 1))
                start, gap = None, 0
    if start is not None:
        runs.append((start, len(active)))
    return runs


def crossing_time(times, trace, lo, hi, start_value, end_value, fraction):
    if not np.isfinite(start_value) or not np.isfinite(end_value):
        return np.nan
    direction = 1.0 if end_value >= start_value else -1.0
    threshold = start_value + fraction * (end_value - start_value)
    values = direction * (trace[lo:hi] - threshold)
    indices = np.flatnonzero(values >= 0.0)
    if len(indices) == 0:
        return np.nan
    return float(times[lo + int(indices[0])])


def event_rows(artist, vibe, sample_rate, envelope_delay, pitch_track, raw):
    artist_delay = envelope_delay(raw, artist, sample_rate)
    vibe_delay = envelope_delay(raw, vibe, sample_rate)
    a = pitch_track(artist, sample_rate)
    v = pitch_track(vibe, sample_rate)
    valid_a = np.isfinite(a[:, 1]) & (a[:, 2] >= 0.55)
    valid_v = np.isfinite(v[:, 1]) & (v[:, 2] >= 0.55)
    at = a[:, 0] / sample_rate - artist_delay / sample_rate
    vt = v[:, 0] / sample_rate - vibe_delay / sample_rate
    use = valid_a & np.isfinite(np.interp(at, vt[valid_v], v[valid_v, 1], left=np.nan, right=np.nan))
    indices = np.flatnonzero(use)
    if len(indices) < 32:
        return [], artist_delay, vibe_delay

    times = at[indices]
    artist_notes = smooth(midi(a[indices, 1]))
    vibe_notes = smooth(midi(np.interp(times, vt[valid_v], v[valid_v, 1])) )
    # An event needs >=25 ct net movement across 8 adjacent 1.33-ms samples.
    lookahead = 8
    activity = np.zeros(len(times), dtype=bool)
    activity[:-lookahead] = np.abs(artist_notes[lookahead:] - artist_notes[:-lookahead]) >= 0.25
    rows = []
    for begin, end in merge_runs(activity):
        # Expand into stable pre/post regions; reject tracker wobble.
        left = max(0, begin - 45)
        right = min(len(times), end + 150)
        pre_lo, pre_hi = left, max(left + 1, begin - 6)
        post_lo, post_hi = min(right - 1, end + 28), right
        if post_hi - post_lo < 8 or pre_hi - pre_lo < 8:
            continue
        artist_start = float(np.nanmedian(artist_notes[pre_lo:pre_hi]))
        artist_end = float(np.nanmedian(artist_notes[post_lo:post_hi]))
        if abs(artist_end - artist_start) < 0.50:
            continue
        vibe_start = float(np.nanmedian(vibe_notes[pre_lo:pre_hi]))
        vibe_end = float(np.nanmedian(vibe_notes[post_lo:post_hi]))
        artist_t10 = crossing_time(times, artist_notes, left, right, artist_start, artist_end, 0.10)
        artist_t50 = crossing_time(times, artist_notes, left, right, artist_start, artist_end, 0.50)
        artist_t90 = crossing_time(times, artist_notes, left, right, artist_start, artist_end, 0.90)
        vibe_t10 = crossing_time(times, vibe_notes, left, right, vibe_start, vibe_end, 0.10)
        vibe_t50 = crossing_time(times, vibe_notes, left, right, vibe_start, vibe_end, 0.50)
        vibe_t90 = crossing_time(times, vibe_notes, left, right, vibe_start, vibe_end, 0.90)
        if not np.isfinite(artist_t50) or not np.isfinite(vibe_t50):
            continue
        rows.append({
            "time_seconds": round(float(times[begin]), 6),
            "direction": "up" if artist_end > artist_start else "down",
            "artist_step_cents": round((artist_end - artist_start) * 100.0, 2),
            "vibe_step_cents": round((vibe_end - vibe_start) * 100.0, 2),
            "artist_t10_ms": round(artist_t10 * 1000.0, 3),
            "artist_t50_ms": round(artist_t50 * 1000.0, 3),
            "artist_t90_ms": round(artist_t90 * 1000.0, 3),
            "vibe_t10_ms": round(vibe_t10 * 1000.0, 3),
            "vibe_t50_ms": round(vibe_t50 * 1000.0, 3),
            "vibe_t90_ms": round(vibe_t90 * 1000.0, 3),
            "vibe_minus_artist_t10_ms": round((vibe_t10 - artist_t10) * 1000.0, 3),
            "vibe_minus_artist_t50_ms": round((vibe_t50 - artist_t50) * 1000.0, 3),
            "vibe_minus_artist_t90_ms": round((vibe_t90 - artist_t90) * 1000.0, 3),
        })
    return rows, artist_delay, vibe_delay


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("vibe_report", type=Path)
    parser.add_argument("artist_report", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pitch-tools", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.pitch_tools))
    from measure_artist_vibe_latency_aligned import envelope_delay, read_mono
    from compare_pitch_correction_bounces import pitch_track

    args.output.mkdir(parents=True, exist_ok=True)
    sample_rate, raw = read_mono(args.raw)
    vibe = {case_key(row): row for row in load_report(args.vibe_report)}
    artist = {case_key(row): row for row in load_report(args.artist_report)}
    events, summary = [], []
    for key in sorted(vibe.keys() & artist.keys(), key=lambda x: tuple(float(v) for v in x)):
        _, artist_signal = read_mono(Path(artist[key]["output"]))
        _, vibe_signal = read_mono(Path(vibe[key]["output"]))
        rows, artist_delay, vibe_delay = event_rows(artist_signal, vibe_signal, sample_rate,
                                                     envelope_delay, pitch_track, raw)
        for row in rows:
            row.update(dict(zip(("retune_ms", "flex_tune", "humanize", "natural_vibrato"), key)))
        events.extend(rows)
        t50 = [row["vibe_minus_artist_t50_ms"] for row in rows]
        t90 = [row["vibe_minus_artist_t90_ms"] for row in rows]
        summary.append({
            "retune_ms": key[0], "flex_tune": key[1], "humanize": key[2], "natural_vibrato": key[3],
            "events": len(rows), "artist_envelope_delay_samples": artist_delay,
            "vibe_envelope_delay_samples": vibe_delay,
            "median_vibe_minus_artist_t50_ms": round(float(np.median(t50)), 3) if t50 else "",
            "median_vibe_minus_artist_t90_ms": round(float(np.median(t90)), 3) if t90 else "",
        })
    fields = ["retune_ms", "flex_tune", "humanize", "natural_vibrato", "time_seconds", "direction",
              "artist_step_cents", "vibe_step_cents", "artist_t10_ms", "artist_t50_ms", "artist_t90_ms",
              "vibe_t10_ms", "vibe_t50_ms", "vibe_t90_ms", "vibe_minus_artist_t10_ms",
              "vibe_minus_artist_t50_ms", "vibe_minus_artist_t90_ms"]
    with (args.output / "transition-events.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(events)
    with (args.output / "transition-summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary[0].keys()); writer.writeheader(); writer.writerows(summary)
    print(f"events={len(events)}")
    print(args.output / "transition-summary.csv")


if __name__ == "__main__":
    main()
