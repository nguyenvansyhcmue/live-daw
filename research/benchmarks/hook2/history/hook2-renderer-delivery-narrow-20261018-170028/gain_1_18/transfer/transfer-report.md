# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6794
- Global correction-transfer slope: 0.9907 (4491 fit frames)
- Global median absolute movement error: 6.03 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.9907 | 6.03 | 27.71 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1419 | -0.74 | 4.62 |
| 10-25 cents | 2658 | 1.13 | 4.31 |
| 25-50 cents | 1916 | 2.82 | 9.00 |
| 50-100 cents | 799 | -10.16 | 16.76 |
| 100-200 cents | 2 | 134.44 | 134.44 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
