# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6803
- Global correction-transfer slope: 0.7870 (4500 fit frames)
- Global median absolute movement error: 4.50 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.7870 | 4.50 | 28.67 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1421 | -1.18 | 4.65 |
| 10-25 cents | 2654 | -0.15 | 3.63 |
| 25-50 cents | 1914 | 0.38 | 4.59 |
| 50-100 cents | 810 | -3.78 | 11.00 |
| 100-200 cents | 2 | 151.39 | 151.39 |
| 200-400 cents | 2 | -138.93 | 142.83 |
| 400+ cents | 0 | nan | nan |
