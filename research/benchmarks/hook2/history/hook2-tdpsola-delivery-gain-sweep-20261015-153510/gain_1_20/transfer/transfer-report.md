# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6729
- Global correction-transfer slope: 0.9432 (4453 fit frames)
- Global median absolute movement error: 7.74 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.9432 | 7.74 | 34.35 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1412 | -3.35 | 6.23 |
| 10-25 cents | 2625 | 0.31 | 5.69 |
| 25-50 cents | 1899 | 4.01 | 10.17 |
| 50-100 cents | 791 | -8.87 | 23.18 |
| 100-200 cents | 2 | 78.34 | 78.34 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
