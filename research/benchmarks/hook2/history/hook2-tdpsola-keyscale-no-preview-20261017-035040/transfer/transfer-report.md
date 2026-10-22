# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6803
- Global correction-transfer slope: 0.7833 (4497 fit frames)
- Global median absolute movement error: 4.39 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.7833 | 4.39 | 25.03 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1422 | -0.90 | 4.44 |
| 10-25 cents | 2655 | -0.20 | 3.53 |
| 25-50 cents | 1920 | 0.33 | 4.43 |
| 50-100 cents | 803 | -3.67 | 10.42 |
| 100-200 cents | 2 | 127.31 | 127.31 |
| 200-400 cents | 1 | 5.47 | 5.47 |
| 400+ cents | 0 | nan | nan |
