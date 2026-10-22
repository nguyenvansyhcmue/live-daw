# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6789
- Global correction-transfer slope: 0.8376 (4490 fit frames)
- Global median absolute movement error: 4.31 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8376 | 4.31 | 25.29 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1417 | -1.39 | 4.52 |
| 10-25 cents | 2656 | -0.12 | 3.45 |
| 25-50 cents | 1909 | 0.15 | 4.40 |
| 50-100 cents | 805 | -3.82 | 10.17 |
| 100-200 cents | 2 | 138.33 | 138.33 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
