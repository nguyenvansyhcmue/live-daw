# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6835
- Global correction-transfer slope: 0.4874 (4514 fit frames)
- Global median absolute movement error: 8.28 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.4874 | 8.28 | 46.77 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1439 | -0.57 | 5.78 |
| 10-25 cents | 2651 | -1.35 | 6.67 |
| 25-50 cents | 1923 | -2.85 | 10.98 |
| 50-100 cents | 815 | 1.99 | 29.96 |
| 100-200 cents | 5 | 123.94 | 140.70 |
| 200-400 cents | 2 | -285.35 | 285.35 |
| 400+ cents | 0 | nan | nan |
