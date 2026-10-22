# Hook-2 correction-transfer analysis

Each bounce is aligned independently to the raw vocal before measuring pitch movement. A slope of 1.0 means Vibe applies the same cents movement as the Artist reference; this does not compare waveform phase or fixed latency.

- Shared configurations: 24
- Reliable voiced frames: 163573
- Global correction-transfer slope: 0.3191 (92439 fit frames)
- Global median absolute movement error: 13.60 cents

| Case | Controls (R/F/H/N) | slope | median |error| | p90 |error| |
|---:|---|---:|---:|---:|
| 0 | 0/0/0/0 | 0.4860 | 8.39 | 48.28 |
| 2 | 25/0/0/0 | 0.7579 | 9.42 | 45.88 |
| 21 | 25/50/50/3 | 0.2180 | 9.92 | 45.17 |
| 1 | 10/0/0/0 | 0.5085 | 10.36 | 50.89 |
| 20 | 10/25/25/0 | 0.7545 | 10.55 | 42.25 |
| 8 | 0/100/0/0 | nan | 10.89 | 60.60 |
| 19 | 0/0/0/12 | 0.2456 | 11.30 | 77.57 |
| 6 | 0/50/0/0 | 0.4385 | 11.71 | 48.74 |
| 18 | 0/0/0/9 | 0.2867 | 11.79 | 66.05 |
| 4 | 100/0/0/0 | 1.0489 | 11.85 | 46.86 |
| 17 | 0/0/0/6 | 0.3249 | 12.70 | 62.66 |
| 7 | 0/75/0/0 | 0.1782 | 13.00 | 52.23 |
| 22 | 50/75/75/6 | -0.8782 | 13.43 | 80.54 |
| 16 | 0/0/0/3 | 0.3241 | 14.04 | 61.68 |
| 10 | 0/0/50/0 | 0.5362 | 15.34 | 55.88 |
| 9 | 0/0/25/0 | 0.5236 | 15.37 | 57.08 |
| 3 | 50/0/0/0 | 0.8832 | 15.52 | 54.85 |
| 11 | 0/0/75/0 | 0.5425 | 15.66 | 57.05 |
| 5 | 0/25/0/0 | 0.5410 | 15.77 | 54.04 |
| 12 | 0/0/100/0 | 0.5551 | 15.83 | 56.55 |
| 23 | 100/100/100/12 | -0.7595 | 19.18 | 109.55 |
| 15 | 0/0/0/-6 | 0.3229 | 20.15 | 69.18 |
| 14 | 0/0/0/-9 | 0.2614 | 23.18 | 77.49 |
| 13 | 0/0/0/-12 | 0.2012 | 25.50 | 84.22 |

## By Artist correction magnitude

| Artist movement | Frames | Vibe − Artist median | median absolute error |
|---|---:|---:|---:|
| 0-10 cents | 49792 | 0.94 | 10.10 |
| 10-25 cents | 60629 | 0.26 | 12.04 |
| 25-50 cents | 38769 | -0.41 | 16.70 |
| 50-100 cents | 12613 | -6.46 | 42.55 |
| 100-200 cents | 1665 | -54.10 | 141.09 |
| 200-400 cents | 91 | -192.05 | 197.02 |
| 400+ cents | 14 | -382.26 | 398.20 |
