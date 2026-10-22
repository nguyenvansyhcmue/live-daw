# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6788
- Global correction-transfer slope: 0.8260 (4487 fit frames)
- Global median absolute movement error: 4.44 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8260 | 4.44 | 24.78 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1419 | -1.35 | 4.70 |
| 10-25 cents | 2656 | -0.01 | 3.58 |
| 25-50 cents | 1910 | 0.18 | 4.57 |
| 50-100 cents | 801 | -3.72 | 10.64 |
| 100-200 cents | 2 | 136.54 | 136.54 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
