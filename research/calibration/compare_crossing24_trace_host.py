#!/usr/bin/env python3
"""Compare diagnostic and host renders using the same pitch/event analyser."""
import csv
import hashlib
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ROOT = Path('/Users/hiimdrdey/autotune')
SOURCE = Path('/Users/hiimdrdey/code/daw/autotune')
TRACE = ROOT / 'artifacts/crossing24-worst-transitions-20261017-111756/full_default_render.wav'
HOST = ROOT / 'artifacts/hook2-tdpsola-renderer-crossing-preview-sweep-20261017-103839/crossing_24ms/vibe/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav'
RAW = Path('/Users/hiimdrdey/Downloads/hook 2raw.wav')
OUT = ROOT / 'artifacts/crossing24-trace-host-comparison'
sys.path[:0] = [str(ROOT), str(SOURCE / 'tools')]
from fit_studioforge_transitions import event_rows
from compare_pitch_correction_bounces import pitch_track
from measure_artist_vibe_latency_aligned import envelope_delay, read_mono

def normalize(samples):
    if np.issubdtype(samples.dtype, np.integer):
        return samples.astype(np.float64) / float(max(abs(np.iinfo(samples.dtype).min), np.iinfo(samples.dtype).max))
    return samples.astype(np.float64)

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rate_raw, raw = read_mono(RAW)
    rate_trace, trace = read_mono(TRACE)
    rate_host, host = read_mono(HOST)
    if len({rate_raw, rate_trace, rate_host}) != 1:
        raise SystemExit('Sample rates do not match')
    n = min(len(trace), len(host))
    x, y = trace[:n], host[:n]
    gain = float(np.dot(x, y) / np.dot(x, x))
    residual = float(np.linalg.norm(y - gain * x) / np.linalg.norm(y))
    corr = float(np.corrcoef(x, y)[0, 1])
    rows, host_delay, trace_delay = event_rows(host, trace, rate_raw, envelope_delay, pitch_track, raw)
    with (OUT / 'host-vs-trace-events.csv').open('w', newline='') as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    t50 = [abs(r['vibe_minus_artist_t50_ms']) for r in rows]
    lines = [
        '# Diagnostic trace versus DAW host bounce',
        f'- Sample rate: {rate_raw} Hz',
        f'- Raw envelope delays: host {host_delay} samples, trace {trace_delay} samples',
        f'- Trace-to-host least-squares gain: {gain:.6f}',
        f'- Correlation: {corr:.6f}',
        f'- Gain-fitted residual RMS / host RMS: {residual:.6f}',
        f'- Matched host-anchored transition events: {len(rows)}',
        f'- Median absolute t50 offset: {np.median(t50):.3f} ms' if t50 else '- No matched transitions',
        '- Matching events are not independent transition counts; no equivalence is assumed.',
        '- Trace PCM16 and host PCM24, host routing and plugin wrapper can affect waveform comparison.',
        '',
        '## Provenance',
        f'- Raw SHA-256: {sha(RAW)}',
        f'- Trace SHA-256: {sha(TRACE)}',
        f'- Host SHA-256: {sha(HOST)}',
    ]
    (OUT / 'comparison.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
