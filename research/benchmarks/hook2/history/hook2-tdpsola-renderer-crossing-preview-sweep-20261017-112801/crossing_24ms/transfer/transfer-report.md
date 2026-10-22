# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6799
- Global correction-transfer slope: 0.8403 (4500 fit frames)
- Global median absolute movement error: 4.33 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8403 | 4.33 | 22.63 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1418 | -1.28 | 4.36 |
| 10-25 cents | 2656 | -0.11 | 3.49 |
| 25-50 cents | 1917 | 0.03 | 4.44 |
| 50-100 cents | 806 | -3.74 | 10.10 |
| 100-200 cents | 2 | 139.88 | 139.88 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
