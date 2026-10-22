# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6790
- Global correction-transfer slope: 0.8443 (4493 fit frames)
- Global median absolute movement error: 4.33 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8443 | 4.33 | 24.92 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1416 | -1.28 | 4.38 |
| 10-25 cents | 2655 | -0.11 | 3.53 |
| 25-50 cents | 1913 | 0.25 | 4.56 |
| 50-100 cents | 804 | -3.60 | 10.27 |
| 100-200 cents | 2 | 139.59 | 139.59 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
