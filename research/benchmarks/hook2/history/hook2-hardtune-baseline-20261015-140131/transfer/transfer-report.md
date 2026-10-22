# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6830
- Global correction-transfer slope: 0.4868 (4511 fit frames)
- Global median absolute movement error: 8.39 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.4868 | 8.39 | 48.05 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1434 | -0.41 | 6.38 |
| 10-25 cents | 2652 | -1.33 | 6.68 |
| 25-50 cents | 1922 | -2.80 | 10.89 |
| 50-100 cents | 815 | 1.92 | 29.99 |
| 100-200 cents | 5 | 123.35 | 143.26 |
| 200-400 cents | 2 | -290.87 | 290.87 |
| 400+ cents | 0 | nan | nan |
