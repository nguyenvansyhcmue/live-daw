# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6747
- Global correction-transfer slope: 0.7670 (4456 fit frames)
- Global median absolute movement error: 6.78 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.7670 | 6.78 | 31.29 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1408 | -3.53 | 6.64 |
| 10-25 cents | 2644 | -2.01 | 5.78 |
| 25-50 cents | 1906 | 0.27 | 6.52 |
| 50-100 cents | 787 | -6.95 | 15.38 |
| 100-200 cents | 2 | 256.68 | 256.68 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
