#!/usr/bin/env python3
"""Compare the first Hook-2 phrase with later phrases on one alignment clock."""
import argparse
import json
from pathlib import Path

import numpy as np
from diagnose_vocal_texture_ab import delay_against, frame_metrics, read_mono, trim_delay


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--artist", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rate, raw = read_mono(args.raw)
    artist_rate, artist = read_mono(args.artist)
    candidate_rate, candidate = read_mono(args.candidate)
    if rate != artist_rate or rate != candidate_rate:
        raise SystemExit("sample rates differ")

    artist_delay = delay_against(raw, artist, rate)
    candidate_delay = delay_against(raw, candidate, rate)
    length = min(len(raw), len(artist) - artist_delay, len(candidate) - candidate_delay)
    artist = trim_delay(artist, artist_delay, length)
    candidate = trim_delay(candidate, candidate_delay, length)

    windows = ((0, 2), (2, 4), (4, 6), (6, 8), (8, 10))
    rows = []
    for begin, end in windows:
        start_sample = round(begin * rate)
        stop_sample = min(round(end * rate), length)
        if stop_sample - start_sample < 4096:
            continue
        reference = artist[start_sample:stop_sample]
        test = candidate[start_sample:stop_sample]
        metrics, autocorr = frame_metrics(reference, test, rate, f"{begin}-{end}s")
        lag_ms, artist_ac, candidate_ac = map(np.asarray, zip(*autocorr))
        positive = candidate_ac - artist_ac
        peak = int(np.argmax(np.abs(positive)))
        rows.append({
            "window_seconds": [begin, end],
            "artist_rms": float(np.sqrt(np.mean(reference ** 2))),
            "candidate_rms": float(np.sqrt(np.mean(test ** 2))),
            "texture": metrics,
            "largest_autocorrelation_delta": {
                "lag_ms": float(lag_ms[peak]),
                "candidate_minus_artist": float(positive[peak]),
            },
        })
    report = {
        "artist_delay_samples_from_raw": artist_delay,
        "candidate_delay_samples_from_raw": candidate_delay,
        "windows": rows,
        "note": "Autocorrelation difference is an artifact clue, not proof of a delayed dry/wet copy.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
