# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6796
- Global correction-transfer slope: 0.7932 (4493 fit frames)
- Global median absolute movement error: 4.63 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.7932 | 4.63 | 27.14 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1421 | -1.35 | 4.58 |
| 10-25 cents | 2654 | -0.30 | 3.79 |
| 25-50 cents | 1916 | 0.30 | 4.82 |
| 50-100 cents | 801 | -3.61 | 10.54 |
| 100-200 cents | 2 | 149.71 | 149.71 |
| 200-400 cents | 2 | -133.78 | 138.21 |
| 400+ cents | 0 | nan | nan |
