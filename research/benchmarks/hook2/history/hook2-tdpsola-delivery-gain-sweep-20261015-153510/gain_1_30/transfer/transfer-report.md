# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6730
- Global correction-transfer slope: 0.9961 (4452 fit frames)
- Global median absolute movement error: 9.68 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.9961 | 9.68 | 37.72 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1415 | -3.52 | 6.33 |
| 10-25 cents | 2622 | 1.50 | 6.91 |
| 25-50 cents | 1904 | 8.47 | 12.12 |
| 50-100 cents | 787 | -13.15 | 28.92 |
| 100-200 cents | 2 | 54.37 | 66.23 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
