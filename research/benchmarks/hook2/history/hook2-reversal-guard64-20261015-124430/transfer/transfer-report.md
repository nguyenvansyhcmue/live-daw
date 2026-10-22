# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 24
- Reliable voiced frames: 163642
- Global correction-transfer slope: 0.1998 (92474 fit frames)
- Global median absolute movement error: 13.64 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.4731 | 8.40 | 49.66 |
| 2 | 25/0/0/0 | 0.5289 | 9.49 | 61.69 |
| 21 | 25/50/50/3 | 0.0439 | 9.81 | 55.01 |
| 1 | 10/0/0/0 | 0.3340 | 10.56 | 66.08 |
| 8 | 0/100/0/0 | nan | 10.89 | 60.60 |
| 20 | 10/25/25/0 | 0.5351 | 10.91 | 57.17 |
| 4 | 100/0/0/0 | 0.8701 | 11.40 | 45.29 |
| 6 | 0/50/0/0 | 0.3449 | 11.98 | 55.93 |
| 19 | 0/0/0/12 | 0.0386 | 12.63 | 100.44 |
| 7 | 0/75/0/0 | 0.1760 | 13.04 | 52.39 |
| 18 | 0/0/0/9 | 0.0515 | 13.04 | 92.41 |
| 17 | 0/0/0/6 | 0.0787 | 13.30 | 90.16 |
| 22 | 50/75/75/6 | -0.8812 | 13.52 | 80.57 |
| 16 | 0/0/0/3 | 0.0859 | 14.37 | 81.64 |
| 3 | 50/0/0/0 | 0.5602 | 14.62 | 62.14 |
| 10 | 0/0/50/0 | 0.3332 | 14.77 | 67.79 |
| 9 | 0/0/25/0 | 0.3259 | 14.80 | 68.84 |
| 11 | 0/0/75/0 | 0.3430 | 15.14 | 67.22 |
| 12 | 0/0/100/0 | 0.3568 | 15.34 | 67.70 |
| 5 | 0/25/0/0 | 0.3313 | 15.44 | 65.06 |
| 15 | 0/0/0/-6 | 0.3295 | 18.56 | 72.42 |
| 23 | 100/100/100/12 | -0.7595 | 19.18 | 109.55 |
| 14 | 0/0/0/-9 | 0.3278 | 20.67 | 73.44 |
| 13 | 0/0/0/-12 | 0.2914 | 22.69 | 77.85 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 49806 | 1.00 | 9.97 |
| 10-25 cents | 60650 | 0.03 | 11.81 |
| 25-50 cents | 38815 | -2.48 | 17.51 |
| 50-100 cents | 12597 | 8.46 | 55.75 |
| 100-200 cents | 1666 | -40.87 | 137.96 |
| 200-400 cents | 94 | -170.68 | 181.57 |
| 400+ cents | 14 | -382.03 | 393.01 |
