#!/usr/bin/env python3
"""Locate diagnostic/host divergence without changing either recording."""
import csv
import hashlib
from pathlib import Path
import numpy as np
from scipy.io import wavfile

ROOT = Path('/Users/hiimdrdey/autotune')
TRACE = ROOT / 'artifacts/crossing24-worst-transitions-20261017-111756/full_default_render.wav'
HOST = ROOT / 'artifacts/hook2-tdpsola-renderer-crossing-preview-sweep-20261017-103839/crossing_24ms/vibe/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav'
OUT = ROOT / 'artifacts/crossing24-trace-host-comparison'

def load(path):
    rate, signal = wavfile.read(path)
    if np.issubdtype(signal.dtype, np.integer):
        signal = signal.astype(np.float64) / abs(np.iinfo(signal.dtype).min)
    else:
        signal = signal.astype(np.float64)
    return rate, signal.mean(axis=1) if signal.ndim == 2 else signal

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    rate, trace = load(TRACE)
    host_rate, host = load(HOST)
    if rate != host_rate:
        raise SystemExit('Sample rate mismatch; alignment must be re-established')
    length = min(len(trace), len(host))
    trace, host = trace[:length], host[:length]
    gain = np.dot(trace, host) / np.dot(trace, trace)
    window = rate // 10
    records = []
    for start in range(0, length-window+1, window):
        a, b = trace[start:start+window], host[start:start+window]
        rms = np.sqrt(np.mean(b*b))
        if rms < 0.002: continue
        residual = np.sqrt(np.mean((b-gain*a)**2)) / rms
        denominator = np.linalg.norm(a)*np.linalg.norm(b)
        corr = np.dot(a,b)/denominator if denominator else 0
        records.append((start/rate, rms, residual, corr))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'window-residuals.csv').open('w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['start_s','host_rms','gain_fitted_residual','correlation'])
        writer.writerows(records)
    worst = sorted(records, key=lambda r:r[2], reverse=True)[:10]
    lines = ['# Trace versus host: 100 ms windows', '',
             f'- Sample rate: {rate}; global gain: {gain:.8f}',
             f'- Trace SHA256: {digest(TRACE)}', f'- Host SHA256: {digest(HOST)}',
             '- Windows below host RMS 0.002 are excluded; residual is not a perceptual metric.',
             '', '| Time (s) | RMS | Relative residual | Correlation |', '|---:|---:|---:|---:|']
    lines += [f'| {t:.3f} | {r:.5f} | {e:.4f} | {c:.5f} |' for t,r,e,c in worst]
    (OUT/'window-residuals.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__ == '__main__': main()
