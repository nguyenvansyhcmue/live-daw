# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6832
- Global correction-transfer slope: 0.4859 (4513 fit frames)
- Global median absolute movement error: 8.32 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.4859 | 8.32 | 46.65 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1437 | -0.34 | 6.10 |
| 10-25 cents | 2651 | -1.34 | 6.65 |
| 25-50 cents | 1922 | -2.86 | 10.97 |
| 50-100 cents | 815 | 2.01 | 30.05 |
| 100-200 cents | 5 | 123.35 | 143.26 |
| 200-400 cents | 2 | -290.87 | 290.87 |
| 400+ cents | 0 | nan | nan |
