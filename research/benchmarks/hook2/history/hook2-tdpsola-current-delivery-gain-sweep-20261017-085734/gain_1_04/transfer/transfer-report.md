# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6798
- Global correction-transfer slope: 0.8558 (4497 fit frames)
- Global median absolute movement error: 4.52 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8558 | 4.52 | 24.92 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1418 | -0.86 | 4.40 |
| 10-25 cents | 2658 | 0.09 | 3.49 |
| 25-50 cents | 1916 | 0.51 | 4.69 |
| 50-100 cents | 804 | -5.68 | 11.68 |
| 100-200 cents | 2 | 136.38 | 136.38 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
