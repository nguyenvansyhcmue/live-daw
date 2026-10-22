# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6718
- Global correction-transfer slope: 0.8597 (4458 fit frames)
- Global median absolute movement error: 6.79 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8597 | 6.79 | 30.57 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1409 | -3.57 | 6.28 |
| 10-25 cents | 2607 | -1.15 | 5.37 |
| 25-50 cents | 1904 | 1.90 | 8.30 |
| 50-100 cents | 796 | -10.26 | 18.66 |
| 100-200 cents | 2 | 46.69 | 75.22 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
