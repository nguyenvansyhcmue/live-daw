#!/usr/bin/env python3
"""Create latency-aligned, level-matched blind listening excerpts; no DSP changes."""
from pathlib import Path
import csv
import hashlib
import secrets
import numpy as np
from scipy.io import wavfile

ROOT = Path('/Users/hiimdrdey/autotune')
ARTIST = ROOT / 'artifacts/hook2-artist-vibe-20261014-041857/artist/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav'
VIBE = ROOT / 'artifacts/hook2-tdpsola-renderer-crossing-preview-sweep-20261017-103839/crossing_24ms/vibe/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav'
OUT = ROOT / 'artifacts/hook2-blind-listening-baseline'
WINDOWS = [('01_onset', 0.20, 0.47), ('02_return', 1.42, 1.80),
           ('03_descending', 1.94, 2.28), ('04_tail', 3.82, 4.18),
           ('05_phrase', 3.50, 4.95)]

def load(path):
    rate, x = wavfile.read(path)
    if np.issubdtype(x.dtype, np.integer):
        x = x.astype(np.float64) / float(-np.iinfo(x.dtype).min)
    else:
        x = x.astype(np.float64)
    if x.ndim == 2:
        x = np.mean(x, axis=1)
    return rate, x

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    if OUT.exists():
        raise SystemExit(f'Output already exists; preserving previous blind key: {OUT}')
    ra, a = load(ARTIST)
    rv, v = load(VIBE)
    if ra != 48000 or rv != ra:
        raise SystemExit('Unexpected sample rate; nothing written')
    # Reported raw-relative envelope delays from the accepted host comparison.
    a, v = a[2689:], v[1464:]
    n = min(len(a), len(v))
    a, v = a[:n], v[:n]
    # One gain per complete file: does not erase dynamics inside excerpts.
    rms_a = np.sqrt(np.mean(a*a))
    rms_v = np.sqrt(np.mean(v*v))
    gain_a, gain_v = 1.0, rms_a / rms_v
    peak = max(np.max(np.abs(a * gain_a)), np.max(np.abs(v * gain_v)))
    common = min(1.0, 0.95 / peak) if peak else 1.0
    a, v = a * gain_a * common, v * gain_v * common
    OUT.mkdir(parents=True)
    mapping = []
    for name, start, end in WINDOWS:
        lo, hi = int(start * ra), int(end * ra)
        if hi > n:
            raise SystemExit(f'Window exceeds file: {name}')
        samples = [('Artist', a[lo:hi].copy()), ('Vibe', v[lo:hi].copy())]
        if secrets.randbelow(2):
            samples.reverse()
        fade = min(int(0.005 * ra), (hi-lo)//2)
        for label, (source, clip) in zip(('A', 'B'), samples):
            clip[:fade] *= np.linspace(0, 1, fade)
            clip[-fade:] *= np.linspace(1, 0, fade)
            wavfile.write(OUT / f'{name}_{label}.wav', ra, np.asarray(clip, dtype=np.float32))
            mapping.append((name, label, source, start, end))
    with (OUT / 'answer-key.csv').open('w', newline='') as f:
        w = csv.writer(f); w.writerow(('window', 'clip', 'source', 'raw_start_s', 'raw_end_s')); w.writerows(mapping)
    (OUT / 'provenance.txt').write_text(f'Artist SHA256 {sha(ARTIST)}\nVibe SHA256 {sha(VIBE)}\nArtist delay 2689 samples\nVibe delay 1464 samples\nVibe RMS gain {gain_v:.9f}\nCommon peak gain {common:.9f}\nMono average; 5ms edge fades; float WAV\n')
    print(f'BLIND LISTENING READY: {OUT}')
    print('Compare A and B in each pair. Do not open answer-key.csv before listening.')

if __name__ == '__main__':
    main()
