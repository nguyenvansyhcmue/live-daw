# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6752
- Global correction-transfer slope: 0.7619 (4460 fit frames)
- Global median absolute movement error: 6.69 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.7619 | 6.69 | 31.07 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1408 | -3.56 | 6.51 |
| 10-25 cents | 2647 | -2.16 | 5.71 |
| 25-50 cents | 1908 | 0.26 | 6.68 |
| 50-100 cents | 788 | -6.99 | 15.01 |
| 100-200 cents | 1 | 111.99 | 111.99 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
