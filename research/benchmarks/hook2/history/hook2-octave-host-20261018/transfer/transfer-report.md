# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 24
- Reliable voiced frames: 162447
- Global correction-transfer slope: 0.4095 (91911 fit frames)
- Global median absolute movement error: 14.85 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.8403 | 4.33 | 22.63 |
| 6 | 0/50/0/0 | 0.6577 | 9.74 | 57.82 |
| 18 | 0/0/0/9 | 0.2953 | 11.91 | 75.89 |
| 17 | 0/0/0/6 | 0.3870 | 12.31 | 64.51 |
| 1 | 10/0/0/0 | 0.6710 | 12.52 | 64.90 |
| 19 | 0/0/0/12 | 0.2438 | 12.58 | 86.39 |
| 16 | 0/0/0/3 | 0.3966 | 13.05 | 63.10 |
| 20 | 10/25/25/0 | 0.8118 | 13.50 | 59.93 |
| 2 | 25/0/0/0 | 0.7965 | 13.85 | 66.81 |
| 5 | 0/25/0/0 | 0.7137 | 14.37 | 56.51 |
| 7 | 0/75/0/0 | 0.4447 | 14.87 | 69.01 |
| 21 | 25/50/50/3 | 0.1753 | 14.98 | 72.33 |
| 9 | 0/0/25/0 | 0.5749 | 15.33 | 56.69 |
| 10 | 0/0/50/0 | 0.6133 | 15.57 | 61.22 |
| 11 | 0/0/75/0 | 0.6239 | 15.69 | 62.55 |
| 12 | 0/0/100/0 | 0.6248 | 15.70 | 62.39 |
| 4 | 100/0/0/0 | 1.0857 | 16.61 | 67.91 |
| 15 | 0/0/0/-6 | 0.5380 | 17.15 | 56.46 |
| 14 | 0/0/0/-9 | 0.4854 | 18.73 | 60.39 |
| 8 | 0/100/0/0 | nan | 19.71 | 87.16 |
| 3 | 50/0/0/0 | 0.7743 | 19.92 | 80.91 |
| 22 | 50/75/75/6 | -1.0543 | 20.71 | 95.35 |
| 13 | 0/0/0/-12 | 0.3924 | 21.10 | 68.71 |
| 23 | 100/100/100/12 | -1.0055 | 27.17 | 132.13 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 49239 | 2.09 | 14.80 |
| 10-25 cents | 60504 | 1.37 | 12.39 |
| 25-50 cents | 38537 | -2.47 | 15.18 |
| 50-100 cents | 12508 | -0.61 | 31.12 |
| 100-200 cents | 1586 | -46.23 | 109.07 |
| 200-400 cents | 70 | -121.33 | 121.33 |
| 400+ cents | 3 | 130.47 | 130.47 |
