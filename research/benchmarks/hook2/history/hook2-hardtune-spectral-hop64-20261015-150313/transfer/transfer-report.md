# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6827
- Global correction-transfer slope: 0.4484 (4522 fit frames)
- Global median absolute movement error: 9.30 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.4484 | 9.30 | 47.21 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1422 | -0.99 | 6.56 |
| 10-25 cents | 2657 | -2.51 | 7.73 |
| 25-50 cents | 1930 | -5.49 | 11.73 |
| 50-100 cents | 811 | 1.95 | 31.95 |
| 100-200 cents | 5 | 124.52 | 138.13 |
| 200-400 cents | 2 | -279.85 | 279.85 |
| 400+ cents | 0 | nan | nan |
