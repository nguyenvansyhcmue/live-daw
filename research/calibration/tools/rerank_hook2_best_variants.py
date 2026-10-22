#!/usr/bin/env python3
"""One-clock-method Hook-2 comparison of stored Vibe research bounces.

Different renderers have different *fixed* latency. Estimate each once from
the raw envelope, then score all on the raw-file clock and on the intersection
of the same valid Artist/candidate pitch frames. No DSP or WAV is modified.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import stft


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def signal_at_raw_clock(signal, delay, length):
    begin = max(0, delay)
    end = min(len(signal), begin + length)
    return signal[begin:end]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pitch-tools", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.pitch_tools))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from compare_pitch_correction_bounces import pitch_track
    from measure_artist_vibe_latency_aligned import envelope_delay, read_mono
    from fit_studioforge_transitions import event_rows

    manifest = json.loads(args.manifest.read_text())
    paths = {"artist": Path(manifest["artist"]), **{
        label: Path(path) for label, path in manifest["candidates"].items()}}
    raw_path = Path(manifest["raw"])
    rate, raw = read_mono(raw_path)
    signals = {}
    delays = {}
    tracks = {}
    for label, path in paths.items():
        current_rate, signal = read_mono(path)
        if current_rate != rate:
            raise ValueError(f"sample rate mismatch: {label}")
        signals[label] = signal
        delays[label] = envelope_delay(raw, signal, rate)
        tracks[label] = pitch_track(signal, rate)

    artist_track = tracks["artist"]
    reference_time = (artist_track[:, 0] - delays["artist"]) / rate
    reference_hz = artist_track[:, 1]
    common = np.isfinite(reference_hz) & (reference_hz > 0) & (artist_track[:, 2] >= 0.55)
    estimates = {}
    for label, track in tracks.items():
        if label == "artist":
            continue
        candidate_time = (track[:, 0] - delays[label]) / rate
        valid = np.isfinite(track[:, 1]) & (track[:, 1] > 0) & (track[:, 2] >= 0.55)
        if not np.any(valid):
            raise ValueError(f"no confident pitch frames: {label}")
        estimates[label] = np.interp(reference_time, candidate_time[valid],
                                     track[valid, 1], left=np.nan, right=np.nan)
        common &= np.isfinite(estimates[label]) & (estimates[label] > 0)

    if int(np.count_nonzero(common)) < 100:
        raise ValueError("too few shared voiced frames")
    artist_midi = np.rint(69 + 12 * np.log2(reference_hz[common] / 440))
    common_length = min(len(raw), *(len(signal) - max(0, delays[label])
                                    for label, signal in signals.items()))
    if common_length < rate:
        raise ValueError("insufficient common aligned audio")
    artist_audio = signal_at_raw_clock(signals["artist"], delays["artist"], common_length)

    def high_band_fraction(signal):
        frequencies, _, spectrum = stft(signal, fs=rate, nperseg=2048,
                                         noverlap=1024, boundary=None, padded=False)
        power = np.abs(spectrum) ** 2
        valid_band = (frequencies >= 6000) & (frequencies < 10000)
        return float(power[valid_band].sum() / max(power.sum(), 1e-18))

    artist_high = high_band_fraction(artist_audio)
    results = {}
    for label, predicted in estimates.items():
        error = np.abs(1200 * np.log2(predicted[common] / reference_hz[common]))
        midi = np.rint(69 + 12 * np.log2(predicted[common] / 440))
        candidate_audio = signal_at_raw_clock(signals[label], delays[label], common_length)
        high = high_band_fraction(candidate_audio)
        fixed_delay = lambda source, signal, sample_rate: (
            delays["artist"] if signal is signals["artist"] else delays[label])
        transitions, _, _ = event_rows(signals["artist"], signals[label], rate,
                                       fixed_delay, pitch_track, raw)
        anchors = {}
        for second in (3.855604, 7.542271, 8.356937):
            closest = min(transitions, key=lambda row: abs(row["time_seconds"] - second)) if transitions else None
            anchors[f"{second:.6f}"] = (
                {"matched_event_seconds": closest["time_seconds"],
                 "t10_error_ms": closest["vibe_minus_artist_t10_ms"],
                 "t50_error_ms": closest["vibe_minus_artist_t50_ms"],
                 "t90_error_ms": closest["vibe_minus_artist_t90_ms"]}
                if closest is not None and abs(closest["time_seconds"] - second) < 0.012 else None)
        results[label] = {
            "path": str(paths[label]), "sha256": sha256(paths[label]),
            "delay_from_raw_samples": delays[label],
            "same_note_fraction": float(np.mean(midi == artist_midi)),
            "median_abs_pitch_cents": float(np.median(error)),
            "p90_abs_pitch_cents": float(np.quantile(error, 0.90)),
            "p99_abs_pitch_cents": float(np.quantile(error, 0.99)),
            "highband_6_10k_relative_db": float(10 * np.log10(max(high, 1e-18) / max(artist_high, 1e-18))),
            "anchor_transitions": anchors,
        }
    report = {
        "raw_sha256": sha256(raw_path), "artist_sha256": sha256(paths["artist"]),
        "sample_rate": rate, "common_voiced_frames": int(np.count_nonzero(common)),
        "common_audio_samples": int(common_length),
        "alignment": "each render separately aligned once to raw; common voiced Artist-frame mask",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
