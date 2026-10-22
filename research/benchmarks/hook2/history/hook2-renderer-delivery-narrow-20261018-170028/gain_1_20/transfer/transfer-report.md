# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6789
- Global correction-transfer slope: 0.9988 (4490 fit frames)
- Global median absolute movement error: 6.64 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.9988 | 6.64 | 26.07 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1418 | -0.57 | 4.56 |
| 10-25 cents | 2654 | 1.23 | 4.66 |
| 25-50 cents | 1910 | 3.56 | 9.79 |
| 50-100 cents | 805 | -11.06 | 18.83 |
| 100-200 cents | 2 | 137.15 | 137.15 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
