# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6790
- Global correction-transfer slope: 0.8787 (4490 fit frames)
- Global median absolute movement error: 4.62 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8787 | 4.62 | 25.29 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1420 | -1.08 | 4.17 |
| 10-25 cents | 2652 | 0.09 | 3.38 |
| 25-50 cents | 1909 | 1.05 | 5.22 |
| 50-100 cents | 807 | -6.80 | 11.88 |
| 100-200 cents | 2 | 142.00 | 142.00 |
| 200-400 cents | 0 | nan | nan |
| 400+ cents | 0 | nan | nan |
