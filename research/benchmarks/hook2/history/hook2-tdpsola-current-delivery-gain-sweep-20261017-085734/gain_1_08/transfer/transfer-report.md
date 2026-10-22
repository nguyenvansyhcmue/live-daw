# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6785
- Global correction-transfer slope: 0.9013 (4487 fit frames)
- Global median absolute movement error: 4.83 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.9013 | 4.83 | 25.66 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1418 | -1.21 | 4.65 |
| 10-25 cents | 2650 | 0.35 | 3.57 |
| 25-50 cents | 1910 | 1.12 | 5.51 |
| 50-100 cents | 805 | -5.46 | 11.97 |
| 100-200 cents | 2 | 138.95 | 138.95 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
