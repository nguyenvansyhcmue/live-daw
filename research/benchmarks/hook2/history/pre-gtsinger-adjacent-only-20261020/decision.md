# Adjacent-note midpoint guard: isolated listening candidate

The user's selected app is `../pre-gtsinger-crossing24-listen-20261020/StudioForge Pre-GTSinger Listen.app`; it was not replaced. This candidate was made by copying that exact app chassis and changing only the embedded Vibe VST3. The copy was ad-hoc re-signed and passes `codesign --verify --deep --strict`. A recursive comparison found no other resource differences; the DAW executable itself differs only because re-signing rewrote its signature.

## One DSP change

In `source/VibeAutotune/CorrectionTrajectory.h`, Direct Hard Tune now requires F0 to cross the existing midpoint hysteresis before committing a *one-semitone* target change during a voiced phrase. Onsets and wider melodic jumps retain the original path. Knob mappings, the renderer, sibilance gate, latency configuration, and UI were not changed.

## Hook-2, Alto / F# natural minor, 0/0/0/0

Artist reference, selected Vibe, and candidate WAVs were delay-aligned to the raw input and measured on common valid voiced frames. Absolute pitch-error metrics are relative to Artist, not to the score.

| Raw-input interval | Selected median / P90 / note match | Candidate median / P90 / note match |
| --- | --- | --- |
| 4.0–4.6 s | 11.95 / 97.67 cents / 82.4% | 9.74 / 38.43 cents / 92.4% |
| 7.0–8.0 s | 5.90 / 33.03 cents / 88.6% | 5.79 / 34.26 cents / 89.4% |
| 0.5–10.5 s | 4.44 / 24.24 cents / 94.5% | 4.33 / 22.60 cents / 95.2% |

The candidate fixes the 4.225–4.250 s note mismatch. It is not a perfect match: the 7–8 s P90 is 1.23 cents worse and a few short bins regress. This is an A/B listening candidate, not a production promotion verdict.

`VibeAutotuneCorrectionTrajectoryTest`, `VibeAutotuneLiveControlPipelineTest`, `VibeAutotuneCausalTDPSOLATest`, and `VibeAutotuneKeyScaleLivePathTest` passed in the candidate build. The 24-case Hook-2 host bounce completed. A single Alto-2 holdout host bounce completed but that singer's Artist reference differs by roughly a semitone from both Vibe versions over much of the file; it cannot establish absolute Artist parity. The candidate and selected Vibe were almost identical on that holdout.

A one-sample discontinuity ranking in the requested 4.0–4.6 and 7.0–8.0 s windows found no new standout sample-step peak in the candidate. This is **not** proof that the audible consonant-to-vowel click is gone. The separate experiment disabling the unvoiced burst gate worsened two of three labeled S boundaries and remains rejected. The selected app remains the safe baseline until the new A/B is heard at the reported boundaries.
