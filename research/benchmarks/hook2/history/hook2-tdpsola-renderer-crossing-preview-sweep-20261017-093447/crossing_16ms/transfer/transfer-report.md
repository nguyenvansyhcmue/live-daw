# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6787
- Global correction-transfer slope: 0.8115 (4482 fit frames)
- Global median absolute movement error: 4.43 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8115 | 4.43 | 24.19 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1422 | -1.27 | 4.67 |
| 10-25 cents | 2651 | -0.23 | 3.54 |
| 25-50 cents | 1910 | 0.34 | 4.51 |
| 50-100 cents | 801 | -3.65 | 10.84 |
| 100-200 cents | 1 | 157.17 | 157.17 |
| 200-400 cents | 2 | -133.84 | 138.79 |
| 400+ cents | 0 | nan | nan |
