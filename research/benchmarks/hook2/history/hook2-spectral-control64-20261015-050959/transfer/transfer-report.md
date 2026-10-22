# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 24
- Reliable voiced frames: 163658
- Global correction-transfer slope: 0.2124 (92391 fit frames)
- Global median absolute movement error: 13.53 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.5193 | 8.21 | 45.14 |
| 2 | 25/0/0/0 | 0.5374 | 9.32 | 60.36 |
| 21 | 25/50/50/3 | 0.0475 | 9.77 | 55.10 |
| 1 | 10/0/0/0 | 0.3646 | 10.44 | 65.48 |
| 20 | 10/25/25/0 | 0.5389 | 10.77 | 56.00 |
| 8 | 0/100/0/0 | nan | 10.95 | 60.48 |
| 4 | 100/0/0/0 | 0.8707 | 11.24 | 45.21 |
| 6 | 0/50/0/0 | 0.3567 | 11.99 | 54.93 |
| 19 | 0/0/0/12 | 0.0582 | 12.53 | 96.66 |
| 7 | 0/75/0/0 | 0.1967 | 12.97 | 52.15 |
| 18 | 0/0/0/9 | 0.0724 | 13.02 | 90.66 |
| 17 | 0/0/0/6 | 0.0960 | 13.31 | 88.52 |
| 22 | 50/75/75/6 | -0.8649 | 13.35 | 80.31 |
| 16 | 0/0/0/3 | 0.0980 | 14.33 | 80.42 |
| 3 | 50/0/0/0 | 0.5645 | 14.55 | 61.66 |
| 10 | 0/0/50/0 | 0.3460 | 14.69 | 67.18 |
| 9 | 0/0/25/0 | 0.3385 | 14.71 | 68.63 |
| 11 | 0/0/75/0 | 0.3547 | 15.06 | 66.57 |
| 12 | 0/0/100/0 | 0.3673 | 15.22 | 66.42 |
| 5 | 0/25/0/0 | 0.3402 | 15.37 | 63.91 |
| 15 | 0/0/0/-6 | 0.3385 | 18.50 | 70.96 |
| 23 | 100/100/100/12 | -0.7562 | 19.16 | 109.10 |
| 14 | 0/0/0/-9 | 0.3308 | 20.59 | 72.05 |
| 13 | 0/0/0/-12 | 0.2906 | 22.54 | 77.20 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 49874 | 0.94 | 9.82 |
| 10-25 cents | 60692 | 0.03 | 11.79 |
| 25-50 cents | 38738 | -2.44 | 17.40 |
| 50-100 cents | 12582 | 8.54 | 54.53 |
| 100-200 cents | 1664 | -41.50 | 137.03 |
| 200-400 cents | 94 | -169.24 | 178.17 |
| 400+ cents | 14 | -382.03 | 393.01 |
