# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 24
- Reliable voiced frames: 163654
- Global correction-transfer slope: 0.2005 (92473 fit frames)
- Global median absolute movement error: 13.64 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.4866 | 8.39 | 48.06 |
| 2 | 25/0/0/0 | 0.5289 | 9.49 | 61.69 |
| 21 | 25/50/50/3 | 0.0439 | 9.81 | 55.01 |
| 1 | 10/0/0/0 | 0.3340 | 10.56 | 66.08 |
| 20 | 10/25/25/0 | 0.5351 | 10.91 | 57.17 |
| 8 | 0/100/0/0 | nan | 10.91 | 60.60 |
| 4 | 100/0/0/0 | 0.8701 | 11.40 | 45.29 |
| 6 | 0/50/0/0 | 0.3448 | 11.98 | 55.93 |
| 19 | 0/0/0/12 | 0.0384 | 12.63 | 100.46 |
| 7 | 0/75/0/0 | 0.1779 | 13.04 | 52.39 |
| 18 | 0/0/0/9 | 0.0509 | 13.05 | 92.34 |
| 17 | 0/0/0/6 | 0.0783 | 13.29 | 90.16 |
| 22 | 50/75/75/6 | -0.8812 | 13.52 | 80.57 |
| 16 | 0/0/0/3 | 0.0874 | 14.39 | 81.70 |
| 3 | 50/0/0/0 | 0.5602 | 14.62 | 62.14 |
| 10 | 0/0/50/0 | 0.3335 | 14.78 | 67.75 |
| 9 | 0/0/25/0 | 0.3257 | 14.79 | 68.82 |
| 11 | 0/0/75/0 | 0.3433 | 15.18 | 67.21 |
| 12 | 0/0/100/0 | 0.3573 | 15.33 | 67.72 |
| 5 | 0/25/0/0 | 0.3319 | 15.45 | 65.03 |
| 15 | 0/0/0/-6 | 0.3289 | 18.56 | 72.42 |
| 23 | 100/100/100/12 | -0.7595 | 19.18 | 109.55 |
| 14 | 0/0/0/-9 | 0.3278 | 20.67 | 73.44 |
| 13 | 0/0/0/-12 | 0.2915 | 22.68 | 77.85 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 49822 | 1.00 | 9.98 |
| 10-25 cents | 60646 | 0.03 | 11.81 |
| 25-50 cents | 38812 | -2.49 | 17.50 |
| 50-100 cents | 12601 | 8.46 | 55.74 |
| 100-200 cents | 1665 | -41.47 | 138.07 |
| 200-400 cents | 94 | -170.68 | 181.57 |
| 400+ cents | 14 | -384.48 | 393.01 |
