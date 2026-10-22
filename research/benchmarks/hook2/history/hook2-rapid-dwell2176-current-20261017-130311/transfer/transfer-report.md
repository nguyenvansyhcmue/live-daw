# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6799
- Global correction-transfer slope: 0.8520 (4499 fit frames)
- Global median absolute movement error: 4.22 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8520 | 4.22 | 22.65 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1418 | -1.28 | 4.24 |
| 10-25 cents | 2657 | -0.15 | 3.36 |
| 25-50 cents | 1916 | 0.11 | 4.48 |
| 50-100 cents | 806 | -3.83 | 9.74 |
| 100-200 cents | 2 | 139.97 | 139.97 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
