# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6789
- Global correction-transfer slope: 0.8261 (4488 fit frames)
- Global median absolute movement error: 4.44 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8261 | 4.44 | 25.09 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1417 | -1.34 | 4.69 |
| 10-25 cents | 2658 | -0.01 | 3.57 |
| 25-50 cents | 1911 | 0.18 | 4.55 |
| 50-100 cents | 801 | -3.79 | 10.51 |
| 100-200 cents | 2 | 136.31 | 136.31 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
