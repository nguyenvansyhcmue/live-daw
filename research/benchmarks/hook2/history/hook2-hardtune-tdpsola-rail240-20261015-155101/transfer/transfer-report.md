# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6712
- Global correction-transfer slope: 0.7537 (4456 fit frames)
- Global median absolute movement error: 6.71 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.7537 | 6.71 | 31.32 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1395 | -4.01 | 6.58 |
| 10-25 cents | 2622 | -2.23 | 5.61 |
| 25-50 cents | 1907 | 0.07 | 6.94 |
| 50-100 cents | 786 | -7.01 | 15.28 |
| 100-200 cents | 2 | 256.39 | 256.39 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
