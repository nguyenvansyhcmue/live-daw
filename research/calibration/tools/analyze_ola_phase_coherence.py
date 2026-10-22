#!/usr/bin/env python3
"""Summarize same-output-sample grain agreement from the host OLA ledger."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ledger', type=Path)
    parser.add_argument('--rate', type=int, default=48000)
    args = parser.parse_args()
    by_sample = defaultdict(list)
    with args.ledger.open(newline='') as handle:
        for row in csv.DictReader(handle):
            by_sample[int(row['sample'])].append((float(row['numerator']), float(row['weight'])))
    print('start_s,end_s,samples,mean_grains,phase_agreement,negative_pair_fraction')
    for begin, end in ((1.2, 1.6), (2.7, 3.1), (3.3, 3.7),
                       (5.4, 5.8), (8.3, 8.7), (9.2, 9.6)):
        groups = [values for index, values in by_sample.items()
                  if begin * args.rate <= index < end * args.rate and len(values) >= 2]
        # Compare the two strongest-weight contributions at the same output
        # instant. A positive product means constructive phase agreement.
        pair = [sorted(values, key=lambda pair: pair[1], reverse=True)[:2] for values in groups]
        products = np.array([a[0] * b[0] for a, b in pair])
        energy = np.array([a[0] ** 2 + b[0] ** 2 for a, b in pair])
        # This ratio is weighted by the audible contribution; no unstable
        # per-sample normalization near waveform zero crossings.
        agreement = 2 * np.sum(products) / max(np.sum(energy), 1e-20)
        print(f'{begin},{end},{len(groups)},'
              f'{np.mean([len(values) for values in groups]):.3f},'
              f'{agreement:.6f},{np.mean(products < 0):.6f}')


if __name__ == '__main__':
    main()
