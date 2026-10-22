# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 24
- Reliable voiced frames: 163587
- Global correction-transfer slope: 0.2742 (92532 fit frames)
- Global median absolute movement error: 13.30 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.4868 | 8.39 | 48.05 |
| 8 | 0/100/0/0 | nan | 9.18 | 43.19 |
| 2 | 25/0/0/0 | 0.7580 | 9.45 | 45.97 |
| 1 | 10/0/0/0 | 0.5084 | 10.37 | 50.89 |
| 21 | 25/50/50/3 | 0.1135 | 10.46 | 55.11 |
| 20 | 10/25/25/0 | 0.7545 | 10.55 | 42.25 |
| 7 | 0/75/0/0 | 0.4126 | 11.26 | 43.77 |
| 4 | 100/0/0/0 | 0.8701 | 11.40 | 45.29 |
| 6 | 0/50/0/0 | 0.5121 | 11.82 | 47.34 |
| 22 | 50/75/75/6 | -0.7483 | 12.11 | 74.55 |
| 19 | 0/0/0/12 | 0.0386 | 12.63 | 100.44 |
| 18 | 0/0/0/9 | 0.0515 | 13.04 | 92.41 |
| 17 | 0/0/0/6 | 0.0787 | 13.30 | 90.16 |
| 16 | 0/0/0/3 | 0.0859 | 14.37 | 81.64 |
| 3 | 50/0/0/0 | 0.8889 | 15.11 | 53.12 |
| 10 | 0/0/50/0 | 0.5377 | 15.34 | 55.72 |
| 9 | 0/0/25/0 | 0.5253 | 15.35 | 57.14 |
| 11 | 0/0/75/0 | 0.5425 | 15.67 | 57.25 |
| 12 | 0/0/100/0 | 0.5566 | 15.84 | 56.49 |
| 5 | 0/25/0/0 | 0.5410 | 15.87 | 54.40 |
| 23 | 100/100/100/12 | -0.7053 | 16.38 | 99.17 |
| 15 | 0/0/0/-6 | 0.3295 | 18.56 | 72.42 |
| 14 | 0/0/0/-9 | 0.3278 | 20.67 | 73.44 |
| 13 | 0/0/0/-12 | 0.2914 | 22.69 | 77.85 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 49709 | 1.69 | 9.89 |
| 10-25 cents | 60646 | 0.31 | 11.58 |
| 25-50 cents | 38839 | -0.78 | 16.75 |
| 50-100 cents | 12621 | 0.18 | 53.52 |
| 100-200 cents | 1664 | -40.87 | 137.63 |
| 200-400 cents | 94 | -170.68 | 181.57 |
| 400+ cents | 14 | -382.26 | 394.29 |
