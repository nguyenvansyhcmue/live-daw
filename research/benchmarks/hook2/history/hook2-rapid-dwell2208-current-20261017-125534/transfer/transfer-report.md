# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6802
- Global correction-transfer slope: 0.8523 (4502 fit frames)
- Global median absolute movement error: 4.23 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8523 | 4.23 | 22.55 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1418 | -1.36 | 4.33 |
| 10-25 cents | 2657 | -0.14 | 3.36 |
| 25-50 cents | 1918 | 0.08 | 4.46 |
| 50-100 cents | 807 | -3.72 | 9.82 |
| 100-200 cents | 2 | 139.63 | 139.63 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
