# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6736
- Global correction-transfer slope: 0.8094 (4475 fit frames)
- Global median absolute movement error: 6.63 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8094 | 6.63 | 30.37 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1400 | -3.80 | 6.43 |
| 10-25 cents | 2620 | -2.30 | 5.57 |
| 25-50 cents | 1915 | 0.02 | 6.78 |
| 50-100 cents | 799 | -6.73 | 14.28 |
| 100-200 cents | 2 | 129.11 | 129.11 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
