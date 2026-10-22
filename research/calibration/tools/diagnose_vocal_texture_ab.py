#!/usr/bin/env python3
"""Measure audible texture differences after raw-relative latency alignment.

This is deliberately complementary to F0 tracking.  It does not claim that a
low waveform residual means two pitch renderers are equivalent.  Instead it
reports time-envelope, spectral-shape, modulation, and short-lag correlation
distances against the same reference bounce.  The last metric is evidence for
an audible short delayed/overlapped component, not proof of its DSP cause.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile


def read_mono(path):
    rate, x = wavfile.read(path)
    if np.issubdtype(x.dtype, np.integer):
        x = x.astype(np.float64) / max(abs(np.iinfo(x.dtype).min), np.iinfo(x.dtype).max)
    else:
        x = x.astype(np.float64)
    return rate, x.mean(axis=1) if x.ndim == 2 else x


def rms_env(x, width):
    return np.sqrt(signal.fftconvolve(x * x, np.ones(width) / width, mode="same") + 1e-16)


def delay_against(raw, rendered, rate):
    a = rms_env(raw, max(8, round(.020 * rate)))
    b = rms_env(rendered, max(8, round(.020 * rate)))
    corr = signal.correlate(b, a, mode="full", method="fft")
    lag = np.arange(-len(a) + 1, len(b))
    keep = np.abs(lag) <= round(.100 * rate)
    return int(lag[keep][np.argmax(corr[keep])])


def trim_delay(x, delay, length):
    start = max(0, delay)
    y = x[start:start + length]
    return np.pad(y, (0, max(0, length - len(y))))


def db(x):
    return 20.0 * np.log10(np.maximum(x, 1e-12))


def frame_metrics(reference, candidate, rate, name):
    # Match one global RMS only.  This removes the known ~3 dB delivery-level
    # difference before judging spectral texture; no per-frame normalization.
    rms_gain = float(np.sqrt(np.mean(reference * reference)) /
                     max(np.sqrt(np.mean(candidate * candidate)), 1e-16))
    candidate = candidate * rms_gain
    n_fft, hop = 2048, 256
    f, t, rs = signal.stft(reference, fs=rate, window="hann", nperseg=n_fft,
                           noverlap=n_fft - hop, boundary=None, padded=False)
    _, _, cs = signal.stft(candidate, fs=rate, window="hann", nperseg=n_fft,
                           noverlap=n_fft - hop, boundary=None, padded=False)
    rmag = np.abs(rs) + 1e-12
    cmag = np.abs(cs) + 1e-12
    energy = np.sqrt(np.mean(rmag * rmag, axis=0))
    active = energy > max(np.max(energy) * 0.035, 1e-8)
    freqs = f[:, None]
    def centroid(m): return np.sum(freqs * m, axis=0) / np.sum(m, axis=0)
    def flatness(m): return np.exp(np.mean(np.log(m), axis=0)) / np.mean(m, axis=0)
    def hf_ratio(m):
        all_energy = np.sum(m * m, axis=0)
        high = np.sum((m[f >= 5000] ** 2), axis=0)
        return db(np.sqrt(high / np.maximum(all_energy, 1e-14)))
    # Frame-to-frame magnitude change, a useful proxy for grain/handoff roughness.
    rflux = np.sqrt(np.mean(np.diff(np.log(rmag), axis=1) ** 2, axis=0))
    cflux = np.sqrt(np.mean(np.diff(np.log(cmag), axis=1) ** 2, axis=0))
    active_flux = active[1:]
    # Sign/phase can differ legitimately between pitch renderers.  Report the
    # better of normal and polarity-inverted residual but do not use it alone
    # as an audio-quality verdict.
    normal = np.sqrt(np.mean((reference - candidate) ** 2))
    inverted = np.sqrt(np.mean((reference + candidate) ** 2))
    waveform_nrmse = float(min(normal, inverted) / max(np.sqrt(np.mean(reference ** 2)), 1e-12))
    env_r = rms_env(reference, round(.010 * rate))
    env_c = rms_env(candidate, round(.010 * rate))
    env_gain = float(np.dot(env_r, env_c) / max(np.dot(env_c, env_c), 1e-16))
    envelope_nrmse = float(np.sqrt(np.mean((env_r - env_gain * env_c) ** 2)) /
                           max(np.sqrt(np.mean(env_r ** 2)), 1e-12))
    envelope_correlation = float(np.corrcoef(env_r, env_c)[0, 1])
    # Short-lag autocorrelation profile over voiced frames.  This catches a
    # repeat/overlap fingerprint while staying agnostic about the source.
    hp = signal.sosfilt(signal.butter(3, 600, btype="highpass", fs=rate, output="sos"), reference)
    hc = signal.sosfilt(signal.butter(3, 600, btype="highpass", fs=rate, output="sos"), candidate)
    lags = np.arange(round(.001 * rate), round(.025 * rate) + 1)
    ac_r, ac_c = [], []
    for lag in lags:
        a, b = hp[:-lag], hp[lag:]
        u, v = hc[:-lag], hc[lag:]
        ac_r.append(float(np.dot(a, b) / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-15)))
        ac_c.append(float(np.dot(u, v) / max(np.linalg.norm(u) * np.linalg.norm(v), 1e-15)))
    ac_r, ac_c = np.asarray(ac_r), np.asarray(ac_c)
    return {
        "name": name,
        "rms_gain_to_reference": rms_gain,
        "waveform_nrmse_best_polarity": waveform_nrmse,
        "envelope_nrmse_gain_fitted": envelope_nrmse,
        "envelope_correlation": envelope_correlation,
        "active_stft_frames": int(np.sum(active)),
        "log_magnitude_mae_db": float(np.median(np.mean(np.abs(db(rmag[:, active]) - db(cmag[:, active])), axis=0))),
        "spectral_centroid_median_abs_delta_hz": float(np.median(np.abs(centroid(rmag)[active] - centroid(cmag)[active]))),
        "spectral_flatness_median_abs_delta": float(np.median(np.abs(flatness(rmag)[active] - flatness(cmag)[active]))),
        "high_band_ratio_median_abs_delta_db": float(np.median(np.abs(hf_ratio(rmag)[active] - hf_ratio(cmag)[active]))),
        "modulation_flux_median_abs_delta": float(np.median(np.abs(rflux[active_flux] - cflux[active_flux]))),
        "short_lag_autocorr_profile_rmse": float(np.sqrt(np.mean((ac_r - ac_c) ** 2))),
        "short_lag_autocorr_max_abs_delta": float(np.max(np.abs(ac_r - ac_c))),
    }, list(zip(lags / rate * 1000.0, ac_r, ac_c))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--artist", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    rate, raw = read_mono(args.raw)
    ar, artist = read_mono(args.artist)
    cr, candidate = read_mono(args.candidate)
    if ar != rate or cr != rate:
        raise SystemExit("sample-rate mismatch")
    da, dc = delay_against(raw, artist, rate), delay_against(raw, candidate, rate)
    length = min(len(artist) - max(0, da), len(candidate) - max(0, dc), len(raw))
    artist = trim_delay(artist, da, length)
    candidate = trim_delay(candidate, dc, length)
    metrics, autocorr = frame_metrics(artist, candidate, rate, args.label)
    result = {"sample_rate": rate, "artist_delay_samples": da, "candidate_delay_samples": dc,
              "relative_delay_samples": dc - da, "metrics": metrics}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / f"{args.label}-texture.json").write_text(json.dumps(result, indent=2) + "\n")
    with (args.output / f"{args.label}-short-lag-autocorrelation.csv").open("w", newline="") as h:
        w = csv.writer(h); w.writerow(["lag_ms", "artist_correlation", "candidate_correlation"]); w.writerows(autocorr)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
