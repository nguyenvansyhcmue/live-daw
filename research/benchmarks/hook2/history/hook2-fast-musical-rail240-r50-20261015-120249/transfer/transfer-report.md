# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 24
- Reliable voiced frames: 163735
- Global correction-transfer slope: 0.2641 (92522 fit frames)
- Global median absolute movement error: 13.64 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.4868 | 8.39 | 48.05 |
| 2 | 25/0/0/0 | 0.7579 | 9.42 | 45.88 |
| 21 | 25/50/50/3 | 0.0439 | 9.81 | 55.01 |
| 1 | 10/0/0/0 | 0.5085 | 10.36 | 50.89 |
| 20 | 10/25/25/0 | 0.7545 | 10.55 | 42.25 |
| 8 | 0/100/0/0 | nan | 10.89 | 60.60 |
| 4 | 100/0/0/0 | 0.8701 | 11.40 | 45.29 |
| 6 | 0/50/0/0 | 0.4385 | 11.71 | 48.74 |
| 19 | 0/0/0/12 | 0.0386 | 12.63 | 100.44 |
| 7 | 0/75/0/0 | 0.1782 | 13.00 | 52.23 |
| 18 | 0/0/0/9 | 0.0515 | 13.04 | 92.41 |
| 17 | 0/0/0/6 | 0.0787 | 13.30 | 90.16 |
| 22 | 50/75/75/6 | -0.8812 | 13.52 | 80.57 |
| 16 | 0/0/0/3 | 0.0859 | 14.37 | 81.64 |
| 10 | 0/0/50/0 | 0.5362 | 15.34 | 55.88 |
| 9 | 0/0/25/0 | 0.5236 | 15.37 | 57.08 |
| 3 | 50/0/0/0 | 0.8832 | 15.52 | 54.85 |
| 11 | 0/0/75/0 | 0.5425 | 15.66 | 57.05 |
| 5 | 0/25/0/0 | 0.5410 | 15.77 | 54.04 |
| 12 | 0/0/100/0 | 0.5551 | 15.83 | 56.55 |
| 15 | 0/0/0/-6 | 0.3295 | 18.56 | 72.42 |
| 23 | 100/100/100/12 | -0.7595 | 19.18 | 109.55 |
| 14 | 0/0/0/-9 | 0.3278 | 20.67 | 73.44 |
| 13 | 0/0/0/-12 | 0.2914 | 22.69 | 77.85 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 49858 | 1.08 | 10.01 |
| 10-25 cents | 60662 | 0.12 | 11.92 |
| 25-50 cents | 38829 | -0.99 | 16.94 |
| 50-100 cents | 12614 | 0.11 | 53.46 |
| 100-200 cents | 1664 | -40.87 | 137.96 |
| 200-400 cents | 94 | -170.68 | 181.57 |
| 400+ cents | 14 | -382.26 | 395.06 |
