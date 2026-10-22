# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 1
- Reliable voiced frames: 6804
- Global correction-transfer slope: 0.7947 (4496 fit frames)
- Global median absolute movement error: 4.65 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.7947 | 4.65 | 27.34 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 1422 | -1.23 | 4.71 |
| 10-25 cents | 2661 | -0.34 | 3.85 |
| 25-50 cents | 1916 | 0.20 | 4.67 |
| 50-100 cents | 801 | -3.61 | 10.47 |
| 100-200 cents | 2 | 149.42 | 149.42 |
| 200-400 cents | 2 | -133.80 | 138.37 |
| 400+ cents | 0 | nan | nan |
