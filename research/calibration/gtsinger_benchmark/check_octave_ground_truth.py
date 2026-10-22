#!/usr/bin/env python3
"""Offline evidence only: compare host control to independent audio F0 estimates."""
import argparse
import csv
import json
import math
from pathlib import Path

import librosa
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', required=True)
    parser.add_argument('--annotation', required=True)
    parser.add_argument('--trace', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--start', type=float, default=3.8)
    parser.add_argument('--end', type=float, default=4.4)
    args = parser.parse_args()
    audio, sr = librosa.load(args.audio, sr=None, mono=True)
    start = max(0, int((args.start - 0.12) * sr))
    end = min(len(audio), int((args.end + 0.12) * sr))
    segment = audio[start:end]
    hop = 128
    # Both estimates use the same signal; they are not statistically independent
    # of each other, but are independent of the plugin's own detector state.
    yin = librosa.yin(segment, fmin=75, fmax=500, sr=sr, frame_length=2048, hop_length=hop)
    pyin, voiced, _ = librosa.pyin(segment, fmin=75, fmax=500, sr=sr, frame_length=2048, hop_length=hop)
    annotations = json.loads(Path(args.annotation).read_text())
    with open(args.trace, newline='') as f:
        trace = list(csv.DictReader(f))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['audio_time_s', 'yin_hz', 'pyin_hz', 'pyin_voiced', 'score_midi', 'trace_sample_time_s', 'raw_hz', 'stable_hz', 'source_hz', 'source_control_time_s'])
        for i, y in enumerate(yin):
            t = start / sr + i * hop / sr
            if not args.start <= t <= args.end:
                continue
            row = min(trace, key=lambda r: abs(float(r['sampleIndex']) / sr - t))
            score = []
            for a in annotations:
                for n, s, e in zip(a.get('note', []), a.get('note_start', []), a.get('note_end', [])):
                    if s <= t < e and n:
                        score.append(str(n))
            writer.writerow([f'{t:.6f}', f'{y:.3f}', f'{pyin[i]:.3f}' if np.isfinite(pyin[i]) else '', int(voiced[i]), '|'.join(score), f'{float(row["sampleIndex"])/sr:.6f}', row['rawF0'], row['stableF0'], row['sourceControlF0Hz'], f'{float(row["sourceControlTimestamp"])/sr:.6f}'])
    print(f'wrote {output}; audio sample rate={sr}; time columns must be aligned before interpreting source control')


if __name__ == '__main__':
    main()
