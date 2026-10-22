# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6796
- Global correction-transfer slope: 0.7919 (4495 fit frames)
- Global median absolute movement error: 4.52 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.7919 | 4.52 | 29.27 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1419 | -1.39 | 4.59 |
| 10-25 cents | 2655 | -0.29 | 3.64 |
| 25-50 cents | 1909 | 0.41 | 4.64 |
| 50-100 cents | 808 | -3.91 | 10.95 |
| 100-200 cents | 4 | 125.29 | 125.29 |
| 200-400 cents | 1 | 3.69 | 3.69 |
| 400+ cents | 0 | nan | nan |
