# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6799
- Global correction-transfer slope: 0.8360 (4498 fit frames)
- Global median absolute movement error: 4.31 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8360 | 4.31 | 24.29 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1418 | -1.24 | 4.42 |
| 10-25 cents | 2658 | -0.15 | 3.48 |
| 25-50 cents | 1915 | 0.15 | 4.49 |
| 50-100 cents | 806 | -4.09 | 10.50 |
| 100-200 cents | 2 | 138.73 | 138.73 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
