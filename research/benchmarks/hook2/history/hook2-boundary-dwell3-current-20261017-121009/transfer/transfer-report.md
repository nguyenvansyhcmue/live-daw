# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6790
- Global correction-transfer slope: 0.8432 (4494 fit frames)
- Global median absolute movement error: 4.41 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8432 | 4.41 | 22.30 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1415 | -1.32 | 4.50 |
| 10-25 cents | 2653 | -0.18 | 3.59 |
| 25-50 cents | 1913 | 0.06 | 4.49 |
| 50-100 cents | 807 | -3.63 | 10.01 |
| 100-200 cents | 2 | 141.57 | 141.57 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
