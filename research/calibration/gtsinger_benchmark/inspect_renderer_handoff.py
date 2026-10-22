#!/usr/bin/env python3
"""Inspect target-to-render handoff; diagnostic timing is not host timing."""
import argparse
import csv
import math
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1] / 'artifacts/crossing24-bounded-preview-20261017-113341/source/tools'
sys.path.insert(0, str(TOOLS))
from compare_pitch_correction_bounces import pitch_track, read_mono


def num(row, name, fallback=float('nan')):
    try:
        return float(row[name])
    except (KeyError, ValueError, TypeError):
        return fallback


def run(directory, output):
    with (directory / 'case_metrics.csv').open(newline='') as f:
        metrics = next(csv.DictReader(f))
    latency = int(metrics['latencySamples'])
    rate, audio = read_mono(directory / 'full_default_render.wav')
    pitches = pitch_track(audio, rate)
    with (directory / 'full_default_intervals.csv').open(newline='') as f:
        frames = list(csv.DictReader(f))
    with (directory / 'full_default_events.csv').open(newline='') as f:
        commits = [r for r in csv.DictReader(f) if r['event'] == 'target_commit']
    times = np.array([int(r['sampleIndex']) for r in frames])
    results = []
    for i, event in enumerate(commits):
        sample = int(event['sampleIndex'])
        target = int(event['detail'])
        next_sample = int(commits[i + 1]['sampleIndex']) if i + 1 < len(commits) else len(audio)
        start_index = np.searchsorted(times, sample)
        # A target may disappear on a voiced/tracker reset before the next
        # target_commit event.  Never treat that silent/reset interval as a
        # continuous hold of the old note.
        interrupted = next_sample
        for row in frames[start_index:np.searchsorted(times, next_sample)]:
            if int(num(row, 'committedTargetMidi', -1)) != target:
                interrupted = int(row['sampleIndex'])
                break
        stop = min(interrupted, sample + int(0.150 * rate))
        stop_index = np.searchsorted(times, stop)
        window = frames[start_index:stop_index]
        if not window:
            continue
        def first(field, predicate):
            for r in window:
                if predicate(num(r, field)):
                    return (int(r['sampleIndex']) - sample) * 1000 / rate
            return float('nan')
        renderer_ms = first('outputRendererControlTargetMidi', lambda x: x == target)
        spawn_ms = first('spawnTargetMidi', lambda x: x == target)
        grain_ms = first('olaDominantGrainTargetMidi', lambda x: x == target)
        pitch_window = pitches[(pitches[:, 0] >= sample + latency) & (pitches[:, 0] < stop + latency)]
        hz = 440.0 * 2 ** ((target - 69) / 12.0)
        matches = np.isfinite(pitch_window[:, 1]) & (pitch_window[:, 2] >= .55) & (np.abs(1200 * np.log2(np.maximum(pitch_window[:, 1], 1e-12) / hz)) <= 50)
        # Two consecutive frames at this 64-sample analysis hop reduce single-frame detections.
        hits = np.flatnonzero(matches[:-1] & matches[1:]) if len(matches) > 1 else []
        audible_ms = (pitch_window[hits[0], 0] - latency - sample) * 1000 / rate if len(hits) else float('nan')
        first_row = window[0]
        results.append({
            'commit_ms': sample * 1000 / rate, 'target_midi': target,
            'target_lifetime_ms': (interrupted - sample) * 1000 / rate,
            'next_commit_gap_ms': (next_sample - sample) * 1000 / rate,
            'raw_f0_at_commit_hz': num(first_row, 'rawF0'), 'stable_f0_at_commit_hz': num(first_row, 'stableF0'),
            'renderer_control_seen_ms': renderer_ms, 'target_spawn_seen_ms': spawn_ms,
            'target_dominant_grain_seen_ms': grain_ms, 'output_pitch_matches_ms': audible_ms,
            'reliable_output_pitch_frames': int(np.sum(np.isfinite(pitch_window[:, 1]) & (pitch_window[:, 2] >= .55))),
            'active_at_commit': num(first_row, 'correctionIsActive'), 'wet_at_commit': num(first_row, 'dryWetMix'),
        })
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'handoff-events.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(results[0])); w.writeheader(); w.writerows(results)
    print(directory, 'commits', len(results), 'latency_samples', latency)
    for key in ('renderer_control_seen_ms', 'target_spawn_seen_ms', 'target_dominant_grain_seen_ms', 'output_pitch_matches_ms'):
        vals = np.array([r[key] for r in results], dtype=float)
        good = vals[np.isfinite(vals)]
        print(key, 'seen', len(good), '/', len(vals), 'median_ms', round(float(np.median(good)), 2) if len(good) else None)
    print('misses >=40ms reliable:', [(round(r['commit_ms'],1), r['target_midi'], round(r['target_lifetime_ms'],1)) for r in results if r['target_lifetime_ms'] >= 40 and r['reliable_output_pitch_frames'] >= 5 and not math.isfinite(r['output_pitch_matches_ms'])][:20])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('trace', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run(args.trace, args.output)
