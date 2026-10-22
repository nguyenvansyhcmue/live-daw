# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6753
- Global correction-transfer slope: 0.7754 (4466 fit frames)
- Global median absolute movement error: 6.69 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.7754 | 6.69 | 30.45 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1408 | -3.81 | 6.65 |
| 10-25 cents | 2642 | -2.23 | 5.73 |
| 25-50 cents | 1908 | 0.19 | 6.55 |
| 50-100 cents | 793 | -7.11 | 14.73 |
| 100-200 cents | 2 | 258.44 | 258.44 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
