# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6788
- Global correction-transfer slope: 0.9396 (4486 fit frames)
- Global median absolute movement error: 5.46 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.9396 | 5.46 | 25.98 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1422 | -0.85 | 4.16 |
| 10-25 cents | 2649 | 0.75 | 3.90 |
| 25-50 cents | 1918 | 2.26 | 7.46 |
| 50-100 cents | 796 | -10.03 | 15.25 |
| 100-200 cents | 2 | 146.92 | 146.92 |
| 200-400 cents | 1 | 5.52 | 5.52 |
| 400+ cents | 0 | nan | nan |
