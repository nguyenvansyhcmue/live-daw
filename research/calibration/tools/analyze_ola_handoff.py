#!/usr/bin/env python3
"""Validate and measure a same-run TD-PSOLA contribution ledger against its WAV.

The numerator/weight rows are write-side contributions to one output sample.
Their sum is compared with the PCM16 diagnostic WAV at the *same* sample index;
this is not an alignment of independently hosted recordings.  Old/new RMS
describes grain handoff, not the t10/t90 of the audible pitch trajectory.
"""

import argparse
import csv
import math
import struct
import wave
from collections import defaultdict
from pathlib import Path


def read_pcm16_mono(path, first, count):
    with wave.open(str(path), "rb") as source:
        if source.getnchannels() != 1 or source.getsampwidth() != 2:
            raise ValueError("Expected the diagnostic's mono PCM16 WAV")
        if first < 0 or first + count > source.getnframes():
            raise ValueError("OLA sample range falls outside the WAV")
        rate = source.getframerate()
        source.setpos(first)
        pcm = source.readframes(count)
    return rate, [item[0] / 32768.0 for item in struct.iter_unpack("<h", pcm)]


def prefix_squares(values):
    result = [0.0]
    for value in values:
        result.append(result[-1] + value * value)
    return result


def window_rms(prefix, index, half_window):
    start = max(0, index - half_window)
    end = min(len(prefix) - 1, index + half_window + 1)
    return math.sqrt(max(0.0, (prefix[end] - prefix[start]) / (end - start)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("wav", type=Path)
    parser.add_argument("--old-event", required=True,
                        help="One or more comma-separated old-note event IDs")
    parser.add_argument("--new-event", required=True,
                        help="One or more comma-separated new-note event IDs")
    parser.add_argument("--curve-csv", type=Path)
    parser.add_argument("--rms-window-ms", type=float, default=1.0)
    args = parser.parse_args()
    old_events = {int(item) for item in args.old_event.split(",")}
    new_events = {int(item) for item in args.new_event.split(",")}
    if old_events.intersection(new_events):
        raise SystemExit("Old and new event-ID sets must be disjoint")

    contributions = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    with args.ledger.open(newline="") as stream:
        for row in csv.DictReader(stream):
            destination = int(row["destinationSample"])
            event = int(row["targetEventId"])
            pair = contributions[destination][event]
            pair[0] += float(row["numeratorContribution"])
            pair[1] += float(row["weightContribution"])
    if not contributions:
        raise SystemExit("Empty OLA contribution ledger")
    first, last = min(contributions), max(contributions)
    if set(contributions) != set(range(first, last + 1)):
        raise SystemExit("OLA trace has sample gaps: cannot validate its WAV")

    rate, recorded = read_pcm16_mono(args.wav, first, last - first + 1)
    predicted, old, new = [], [], []
    old_present, new_present = [], []
    for destination in range(first, last + 1):
        groups = contributions[destination]
        weight = sum(group[1] for group in groups.values())
        if weight <= 0.0:
            raise SystemExit(f"No OLA weight at output sample {destination}")
        predicted.append(sum(group[0] for group in groups.values()) / weight)
        old.append(sum(groups[event][0] for event in old_events) / weight)
        new.append(sum(groups[event][0] for event in new_events) / weight)
        if any(groups[event][1] > 0.0 for event in old_events):
            old_present.append(destination)
        if any(groups[event][1] > 0.0 for event in new_events):
            new_present.append(destination)
    if not old_present or not new_present:
        raise SystemExit("The requested old/new target event IDs are not both present")

    count = len(predicted)
    mean_pred = sum(predicted) / count
    mean_wav = sum(recorded) / count
    covariance = sum((x - mean_pred) * (y - mean_wav)
                     for x, y in zip(predicted, recorded))
    variance_pred = sum((x - mean_pred) ** 2 for x in predicted)
    variance_wav = sum((y - mean_wav) ** 2 for y in recorded)
    correlation = covariance / math.sqrt(variance_pred * variance_wav)
    rmse = math.sqrt(sum((x - y) ** 2 for x, y in zip(predicted, recorded)) / count)
    overlap = set(old_present).intersection(new_present)
    print(f"clock=output_wav_sample rate={rate}Hz range={first}..{last}")
    print(f"ola_to_wav_correlation={correlation:.9f} rmse={rmse:.9g}")
    print(f"old_events={sorted(old_events)} last_sample={max(old_present)}")
    print(f"new_events={sorted(new_events)} first_sample={min(new_present)}")
    print(f"overlap_samples={len(overlap)} overlap_ms={len(overlap) * 1000 / rate:.3f}")

    half_window = max(0, round(args.rms_window_ms * rate / 2000))
    old_prefix = prefix_squares(old)
    new_prefix = prefix_squares(new)
    if args.curve_csv:
        with args.curve_csv.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("outputSample", "timeMs", "oldContribution", "newContribution",
                             "olaReconstruction", "wavSample", "oldRms", "newRms",
                             "newEnergyShare", "oldNewCrossProduct"))
            for index, destination in enumerate(range(first, last + 1)):
                old_rms = window_rms(old_prefix, index, half_window)
                new_rms = window_rms(new_prefix, index, half_window)
                denominator = old_rms ** 2 + new_rms ** 2
                share = new_rms ** 2 / denominator if denominator else math.nan
                writer.writerow((destination, destination * 1000 / rate,
                                 old[index], new[index], predicted[index], recorded[index],
                                 old_rms, new_rms, share, 2 * old[index] * new[index]))
        print(f"curve={args.curve_csv}")
    print("warning=Grain-energy share is not audible-pitch t10/t90; cross-products "
          "and any non-OLA processing must also be considered.")


if __name__ == "__main__":
    main()
