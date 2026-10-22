# Hook 2 — sustained wet-texture investigation (research only)

Selected app and installed VST3 were not changed. The exact-host baseline was
rebuilt with added read-only OLA telemetry. Its case-0 WAV SHA-256 remains
`1990aca4f64d96cc40abe4aedd3aadc932e6a551b234ccc851342ec23d88590d`,
identical to the selected listening baseline. The research renderer's
`phaseSearchRadius` is back at 0; no candidate was promoted.

## Tested hypothesis

The disabled fine phase search (`phaseSearchRadius=0`) might cause the
whole-song following-voice texture. A radius-2 research build altered 81.6%
of samples but only 6.6% RMS relative to the baseline. Period-to-period
coherence was mixed over six sustained windows: slightly better at 1.2–1.6,
8.3–8.7 and 9.2–9.6 s; slightly worse at 2.7–3.1 and 3.3–3.7 s. This does
not establish a perceptual improvement, so it was rejected.

## Exact-host OLA evidence

`provenance/host-control-0.csv` now records output OLA weight, dominant-grain
weight and phase offset. During fully wet sustained windows the total OLA
weight has p01 about 0.19–0.27, median about 0.67–0.69 and p90 about 0.98.
The window varies, but this alone is not a defect because the renderer divides
the grain sum by total weight. The direct contribution ledger in the previous
baseline trace has two grains on many sampled overlap points; the two strongest
contributions have opposite signs in about 3.6–10.4% of those overlap points.
That is insufficient to call phase cancellation the cause of the audible
following layer. No hard EQ, gate, or OLA-weight change is justified by this
evidence.

## Next discriminating test

Measure the *audible* sideband/secondary-pitch component on several labelled
vowels after fixed latency and level alignment, then compare phase-continuous
and TD-PSOLA renderers from the same host/input. A candidate should be made
only if that metric detects the reported texture and a blinded listen agrees;
it must preserve the selected app's note timing and protected regions.
