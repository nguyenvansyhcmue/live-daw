# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6765
- Global correction-transfer slope: 0.8532 (4472 fit frames)
- Global median absolute movement error: 4.26 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8532 | 4.26 | 23.77 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1414 | -1.16 | 4.38 |
| 10-25 cents | 2645 | -0.13 | 3.53 |
| 25-50 cents | 1904 | 0.31 | 4.33 |
| 50-100 cents | 800 | -3.81 | 10.27 |
| 100-200 cents | 2 | 139.77 | 139.77 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
