# Decision — 2026-10-22

**DO NOT PROMOTE.** Functional new DSP prototype exists; product gate incomplete.

## Measurements through StudioForge

Hook 2: Alto / F# Natural Minor; Retune, Flex, Humanize, Natural Vibrato = 0.
Only voiced/confident frame pairs are compared. Missing F0 is not interpolated
across gaps. Alignment uses an RMS-envelope delay estimate, not ground-truth
sample latency. These scores are not directly interchangeable with historical
reports that used different alignment/interpolation.

| Clip / region | Note match | Median absolute pitch error | P90 |
|---|---:|---:|---:|
| Hook 2 full | 97.74% | 1.11 cents | 7.53 cents |
| Hook 2 0–2 s | 97.74% | 0.88 | 5.08 |
| Hook 2 4.7–5.1 s | 93.67% | 1.61 | 26.46 |
| Hook 2 7–8 s | 94.98% | 1.75 | 12.81 |
| Hook 2 8.25–8.5 s | 99.47% | 2.88 | 11.00 |
| Independent Alto breathy, C minor | 96.94% | 4.22 | 16.71 |
| Independent Alto glissando, C minor | 98.84% | 1.45 | 6.18 |
| Independent Tenor breathy, C major | 98.17% | 1.77 | 6.95 |
| Independent Tenor glissando, F minor | 97.49% | 1.45 | 8.92 |
| Independent Tenor vibrato, C major | 92.75% | 2.53 | 23.83 |

Negative control: unprocessed Hook 2 versus the same Artist reference yields
86.96% note match, median 21.25 cents and P90 55.26 cents. The new result is not
merely unchanged dry audio scoring well; synthetic pitch-delivery tests also
independently verify correction. Different voiced coverage still needs to be
considered when comparing these aggregate numbers.

Hook 2 covers 98.78% of Artist's confidently voiced frames. Independent coverage
is 95.96–98.89%. References are archived Artist bounces; Artist could NOT be
re-rendered in this tool session (AU factory registration failed). This limits
the strength of the same-settings comparison, especially across old versions.

### Transition evidence — failure remains

From `results/v2-audit/transitions.csv`, using the same frame-grid estimator:

| Transition | Artist t10→t90 | New core t10→t90 | Candidate t90 minus Artist |
|---|---:|---:|---:|
| First ascent near 4.72 s | 25.33 ms | 5.33 ms | −2.67 ms |
| Descent near 4.82 s | 5.33 ms | 8.00 ms | −4.00 ms |
| Ascent near 4.89 s | 9.33 ms | 6.67 ms | −1.33 ms |
| Descent near 5.02 s | 6.67 ms | 8.00 ms | 0.00 ms |
| Ascent near 5.08 s | 6.67 ms | 6.67 ms | −4.00 ms |
| Descent near 8.37 s | 8.00 ms | 8.00 ms | +1.33 ms |

Resolution is about 1.33 ms (64 samples at 48 kHz), with additional F0-estimator
bias. These are not direct measurements of hidden Artist target decisions.
There are 29 reference landmark candidates, some with invalid endpoints/low
coverage; this is NOT proof of equal transition counts or complete matching.
The first ascent is much too sharp despite its close landing time.

### Timbre, level and consonants

- Hook 2 RMS is −3.042 dB versus reference; almost all comes from the host's
  measured 0.70710677 track gain. No output limiter or gain boost was inserted
  into DSP to mask this.
- After level matching: 100–500 Hz +0.019 dB; 500–2000 −0.050 dB;
  2–6 kHz −0.136 dB; 6–10 kHz −0.117 dB.
- Cepstral spectral-envelope proxy median absolute difference: 1.081 dB.
  This does NOT prove formants identical or rule out doubled/hollow sound.
- Sample-difference P99.9: Artist 0.07456, level-matched candidate 0.07494.
  Similar values do NOT certify absence of clicks.
- Annotated independent /s/ measurements with strong correlation include
  prominence deltas +0.015, −0.041, +0.273, −0.022, +0.185 and +0.209 dB.
  A weak-correlation /s/ measures −0.598 dB; it is not reliable enough to tune
  against. Some /f/ intervals lack a preceding vowel, so normalized prominence
  is unavailable. There is not yet sufficient /sh/ evidence.
- Listening has NOT been performed or passed by the assistant. Audition
  `results/listen-hook2/Artist.wav` and `Vibe-new-core.wav` at the same level.

## Correctness and realtime evidence

- VST3 and AU build. VST3 ad-hoc signature verifies. Nothing installed.
- Core/contract test executables pass: LPC unity reconstruction, synthetic
  pitch delivery, block 1/64/128/256/1024 invariance, trace invariance,
  Key/Scale/Note Map, state roundtrip, held-MIDI priority, UI construction,
  bypass/reset/reprepare, stereo dynamic-control and non-finite input safety.
- Zero observed `new/new[]` in core processing; no mutex/file I/O in core.
  This allocation test does not prove every third-party wrapper path is safe.
- Trace-on and trace-off WAVs are sample-identical. Final diagnostic WAV remains
  identical after the trace-epoch race fix. Host vs diagnostic after fixed gain:
  max residual 1.19e-7, consistent with 24-bit rounding.
- All inspected real renders and safety tests: zero synthesis fault-guard hits.
- Algorithmic latency: 1780 samples / 37.083 ms at 48 kHz; 1636 at 44.1 kHz;
  3556 at 96 kHz. **Not qualified for ultra-low-latency singing.**
- Offline observed max callback: block 1 = 0.149 ms; 64 = 0.200 ms;
  128 = 0.272 ms; 256 = 0.449 ms; 1024 = 1.589 ms. These are observed maxima,
  not guaranteed WCET. Block 1 exceeds its 0.0208 ms deadline. Average stereo
  processing around 5.9% of realtime at block 64. No device roundtrip measured.

## Measurement bug found in existing host harness

`enumLabel` in the old calibration runner stripped `#`, making F and F# compare
equal. It could accept the wrong key while scanning parameter values. The local
reference runner preserves `#` and logs actual readback:
`voice=Alto key=F# scale=Natural Minor retune=0.0`.

The independent `artist-fsharp-terminal.96sIS0` reference has pitch classes
consistent with F minor rather than F# minor. This supports a configuration
mismatch hypothesis, but does not prove its original runtime preset. It was
excluded from DSP fitting. Natural-key C/F archived fixtures were used instead.
The canonical host source was not edited.

## Exact build and boundaries

Final VST3 executable SHA-256:
`7e1ef7f52ad272fc646d99e4fd14796af9cb2fb6da3e827fe12c7229a26f6d24`

Final host Hook 2 WAV SHA-256:
`8de6266ec336e2c3b57395b54c438f1112732ebed1ee52036b181d918898d723`

Diagnostic trace WAV SHA-256:
`bae416d3b22d29ef485b0cfe254491e75b670d40134ea69614b6c31cdf232f56`

The replacement project has no imported old renderer or runtime engine branch.
Canonical deletion/migration is NOT done: `/Users/hiimdrdey/code/daw` is outside
the writable workspace. The user app, Auto Key, installed Vibe and all archived
audio remain unchanged. There is no new production app/open command to provide.
