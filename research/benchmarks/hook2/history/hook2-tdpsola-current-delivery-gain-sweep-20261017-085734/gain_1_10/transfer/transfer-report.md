# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6751
- Global correction-transfer slope: 0.9218 (4456 fit frames)
- Global median absolute movement error: 4.85 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.9218 | 4.85 | 23.68 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1416 | -0.73 | 4.24 |
| 10-25 cents | 2639 | 0.44 | 3.66 |
| 25-50 cents | 1895 | 1.60 | 5.79 |
| 50-100 cents | 799 | -6.68 | 12.40 |
| 100-200 cents | 2 | 133.02 | 133.02 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
