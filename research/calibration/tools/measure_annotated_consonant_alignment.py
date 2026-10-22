#!/usr/bin/env python3
"""Research comparison: align annotated fricative interiors to the raw source.

Fits one delay per whole annotated phoneme, not one per measurement window.
This is not a blind listening or perceptual-quality test.
"""
import argparse
import csv
import re
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile


def read(path):
    rate, data = wavfile.read(path)
    dtype = data.dtype
    data = data.astype(np.float64)
    if np.issubdtype(dtype, np.integer):
        data /= max(abs(np.iinfo(dtype).min), np.iinfo(dtype).max)
    return rate, data.mean(axis=1) if data.ndim == 2 else data


def phone_intervals(path):
    text = path.read_text()
    match = re.search(r'name = "phone"(.*?)(?=\n\s*item \[\d+\]:|\Z)', text, re.S)
    if not match:
        raise ValueError('No phone tier in TextGrid')
    pattern = r'intervals \[\d+\]:\s*xmin = ([0-9.]+)\s*xmax = ([0-9.]+)\s*text = "([^"]*)"'
    return [(float(a), float(b), label) for a, b, label in re.findall(pattern, match.group(1))]


def rms(x):
    return float(np.sqrt(np.mean(x*x)))


def is_vowel(label):
    # ARPAbet vowel labels in the GTSinger English TextGrid convention carry
    # a stress digit.  This intentionally does not try to label every voiced
    # consonant as a vowel.
    return bool(re.search(r'[0-2]$', label))


def preceding_vowel(intervals, index):
    """Return the closest preceding labelled vowel without jumping a word gap."""
    start = intervals[index][0]
    for candidate in reversed(intervals[:index]):
        c_start, c_end, c_label = candidate
        if start - c_end > 0.120:
            break
        if is_vowel(c_label) and c_end - c_start >= 0.060:
            return candidate
    return None


def central_window(start, end, rate, minimum_seconds=0.040):
    """Use a central vowel slice so consonant boundaries do not set gain."""
    span = end - start
    if span < minimum_seconds:
        return None
    margin = min(0.030, max(0.0, (span - minimum_seconds) / 2.0))
    return round((start + margin)*rate), round((end - margin)*rate)


def robust_vowel_gain_db(artist, vibe, lo, hi, rate):
    """Median 20 ms output-RMS ratios; report spread instead of hiding it."""
    width, hop = round(0.020*rate), round(0.010*rate)
    values = []
    for start in range(lo, hi - width + 1, hop):
        artist_rms, vibe_rms = rms(artist[start:start+width]), rms(vibe[start:start+width])
        if artist_rms > 1.e-7 and vibe_rms > 1.e-7:
            values.append(20*np.log10(artist_rms/vibe_rms))
    if not values:
        return float('nan'), float('nan'), 0
    values = np.asarray(values)
    return float(np.median(values)), float(np.percentile(values, 75)-np.percentile(values, 25)), len(values)


def fit_delay(raw, rendered, lo, hi, min_delay, max_delay):
    template = raw[lo:hi]
    left, right = lo + min_delay, hi + max_delay
    if left < 0 or right > len(rendered):
        raise ValueError('Requested search reaches outside rendered file')
    search = rendered[left:right]
    dots = signal.correlate(search, template, mode='valid', method='fft')
    energies = np.r_[0.0, np.cumsum(search*search)]
    window_power = energies[len(template):] - energies[:-len(template)]
    scores = dots / np.sqrt(np.maximum(window_power * np.dot(template, template), 1e-30))
    i = int(np.argmax(np.abs(scores)))
    return min_delay + i, float(scores[i])


def main():
    ap = argparse.ArgumentParser()
    for name in ('raw', 'artist', 'vibe', 'textgrid', 'output'):
        ap.add_argument('--'+name, type=Path, required=True)
    ap.add_argument('--artist-search', type=int, nargs=2, default=[0, 5000])
    ap.add_argument('--vibe-search', type=int, nargs=2, default=[0, 5000])
    args = ap.parse_args()
    inputs = [read(path) for path in (args.raw, args.artist, args.vibe)]
    sr = inputs[0][0]
    if any(rate != sr for rate, _ in inputs):
        raise ValueError('Different sample rates')
    raw, artist, vibe = [a for _, a in inputs]
    sos = signal.butter(4, 5000, btype='highpass', fs=sr, output='sos')
    raw_h, artist_h, vibe_h = [signal.sosfilt(sos, x) for x in (raw, artist, vibe)]
    intervals = phone_intervals(args.textgrid)
    rows = []
    for interval_index, (start, end, label) in enumerate(intervals):
        if label.upper() not in ('S', 'SH', 'F', 'TH') or end-start < 0.060:
            continue
        # Exclude the first/last 15 ms so transitions are not called fricative interiors.
        lo, hi = round((start + 0.015)*sr), round((end - 0.015)*sr)
        ad, ac = fit_delay(raw_h, artist_h, lo, hi, *args.artist_search)
        vd, vc = fit_delay(raw_h, vibe_h, lo, hi, *args.vibe_search)
        baseline, av, vv = raw_h[lo:hi], artist_h[lo+ad:hi+ad], vibe_h[lo+vd:hi+vd]
        db = lambda x, ref: 20*np.log10(max(rms(x), 1e-12)/max(rms(ref), 1e-12))
        vowel = preceding_vowel(intervals, interval_index)
        gain_db = float('nan')
        gain_iqr_db = float('nan')
        gain_windows = 0
        artist_sibilance_relative_db = float('nan')
        vibe_sibilance_relative_db = float('nan')
        vowel_label = ''
        if vowel is not None:
            vowel_label = vowel[2]
            window = central_window(vowel[0], vowel[1], sr)
            if window is not None:
                v_lo, v_hi = window
                # Use the locally measured consonant delay only as a timing
                # map for the adjacent output.  The gain itself is a ratio
                # of output vowel RMS: no whole-file normalization or raw
                # level enters the Vibe-vs-Artist comparison.
                artist_vowel = artist[v_lo+ad:v_hi+ad]
                vibe_vowel = vibe[v_lo+vd:v_hi+vd]
                if len(artist_vowel) == len(vibe_vowel) and len(artist_vowel):
                    gain_db, gain_iqr_db, gain_windows = robust_vowel_gain_db(
                        artist_vowel, vibe_vowel, 0, len(artist_vowel), sr)
                    # This ratio compares sibilance to the nearby vocal body
                    # within each renderer. It removes arbitrary output gain.
                    artist_sibilance_relative_db = db(av, artist_vowel)
                    vibe_sibilance_relative_db = db(vv, vibe_vowel)
        gain_is_stable = np.isfinite(gain_iqr_db) and gain_iqr_db <= 1.0
        rows.append([label, start, end, vowel_label, ad, ac, vd, vc,
                     db(av, baseline), db(vv, baseline), db(vv, av), gain_db,
                     gain_iqr_db, gain_windows, int(gain_is_stable),
                     db(vv * (10.0**(gain_db/20.0)), av) if gain_is_stable else float('nan'),
                     artist_sibilance_relative_db, vibe_sibilance_relative_db,
                     vibe_sibilance_relative_db - artist_sibilance_relative_db])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['phone','start_s','end_s','preceding_vowel','artist_delay','artist_corr','vibe_delay','vibe_corr',
                    'artist_raw_high_db_unscaled','vibe_raw_high_db_unscaled','vibe_artist_high_db_unscaled',
                    'artist_minus_vibe_vowel_gain_db_median','vowel_gain_iqr_db','vowel_gain_windows',
                    'vowel_gain_is_stable','vibe_artist_high_db_vowel_matched',
                    'artist_sibilance_relative_to_preceding_vowel_db',
                    'vibe_sibilance_relative_to_preceding_vowel_db',
                    'vibe_minus_artist_sibilance_prominence_db'])
        w.writerows(rows)
    print('sample_rate', sr, 'phonemes', len(rows), 'gain_policy=preceding_vowel_output_rms')


if __name__ == '__main__':
    main()
