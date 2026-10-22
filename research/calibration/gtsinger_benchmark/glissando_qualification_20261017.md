# Glissando targeted qualification — 2026-10-17

## Detector rejection attribution (instrumented candidate, not installed)

For the two Glissando_Group clips, the isolated diagnostic was rebuilt with
frame-end timestamps and a bit mask of the existing voicing checks. The DSP
conditions were not changed. Re-rendering both clips produced exactly the
same samples as the pre-instrumentation diagnostic renders. The diagnostic
render had previously been checked against the explicit candidate VST3 host
render (up to host gain and small numeric residual).

Counting each detector frame once and assigning its 1024-sample analysis
window to its centre time gives the following over the annotated glissando
intervals (48 kHz, 128-sample detector hop, F natural minor, Alto, tracking
50, retune/flex/humanize/vibrato 0):

| Clip | Frames | Accepted | Rejected | RMS check failed | Low-band check failed |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0001 | 286 | 105 | 181 | 156 | 79 |
| 0002 | 646 | 158 | 488 | 467 | 319 |

Reasons can overlap: for 0001, 83 frames failed only RMS and 42 failed RMS
and low-band; for 0002, 141 failed only RMS and 255 failed both. These are
counts within labelled glissando intervals, not proof that every analysis
window contains a voiced vowel; the window may straddle a consonant or pause.
The label is not a sample-accurate voicing ground truth. Other failures also
occurred, including raw zero-crossing and raw periodicity checks.

Code inspection identifies a testable feedback hypothesis: rejected frames
update `noiseFloorRms` even when rejection is caused by the RMS threshold
itself. Determine actual RMS, floor, periodicity and thresholds per frame,
and compare voiced-vowel and consonant labels before attempting to change
this policy. Low-band rejection needs separate investigation. Do not simply
lower both thresholds: that could tune /s/, breath and noise.

The instrumented output is in `/private/tmp/gtsinger-reject-0001` and
`/private/tmp/gtsinger-reject-0002`; these are temporary. The diagnostic code
is in the candidate source under `artifacts/crossing24-bounded-preview-20261017-113341/source`.
No plug-in was installed or promoted. This result does not establish sonic
equivalence to Artist, and the historical Artist bounce lacks verified binary
hash and parameter readback.

## Periodic-frame noise-floor guard experiment — rejected

An isolated experiment prevented updating the floor on rejected frames only
when raw periodicity >= 0.75 and the existing filtered periodicity and
correlation tests passed. It did not change the remaining voicing gates.
This change was reverted after testing; it was never installed.

Phone labels were taken from the dataset TextGrid and counted only when the
entire 1024-sample analysis frame lay inside a phone. Accepted vowel frames
increased from 693/1281 to 1054/1281 on clip 0001 and from 574/1232 to
743/1232 on clip 0002. Accepted sibilant frames increased from 8/236 to
11/236 on 0001 and remained 0/67 on 0002. Labels are not proof of audible
artifacts, but the change requires closer consonant qualification.

Against the historical Artist bounce, aligned tagged-glissando pitch error
changed from median/p90 37.792/83.131 to 22.572/75.027 cents on 0001, but
from 75.697/97.108 to 77.564/98.142 cents on 0002. The two variants used
486/488 and 1229/1226 valid pitch frames respectively. Artist provenance is
not verified, and comparing medians across slightly different valid-frame
sets is a limitation. The script `compare_detector_guard.py` reproduces this
diagnostic while temporary renders remain present.

The key/scale live-path test passed for the experimental build. The end-to-end
test failed with `100 ms retune was not slower than 25 ms`; the baseline
produced the same failure, so it cannot be attributed to this guard without
further investigation. Neither build is qualified by that test result.
For one downward test tone, the test's first 99%-progress crossing was
1205.333 ms at both 25 and 100 ms, so its strict inequality fails; the
63%-progress crossings were 53.333 and 117.333 ms respectively. The test
computes progress using 2048-sample pitch-estimation windows and a 512-sample
step. This suggests the 99% metric needs independent examination; it does
not establish that either the DSP or the assertion is correct.
Hook 2 produced 43 target commits in both the baseline and experiment using
the same diagnostic configuration. This count is not the same as the
separately measured output transition count, and must not be compared directly
with Artist's output transition count.

Conclusion: floor contamination is a real mechanism worth investigation, but
the first guard is not a general solution; it can increase vowel coverage
without consistently improving the output against the reference. Avoid a
global threshold/floor change until target selection and renderer behavior
for the newly voiced frames have been examined and regressions pass.

## Low-band veto interaction — second isolated experiment

In clip 0002 from 5.1–5.9 seconds, the historical Artist pitch estimate was
most often MIDI 68 or 70 while both baseline and first-guard Vibe estimates
were mostly MIDI 69 (outside F natural minor). Over 300 distinct detector
frames in that interval, the median raw periodicity was 0.9944, while the
median preprocessed/raw RMS ratio was 0.246, below the 0.27 low-band cutoff.
237 frames failed that cutoff despite raw periodicity >= 0.75. The trace also
showed mostly no active correction or wet output. These are observations,
not proof that the Artist reference used the same settings.

The second experiment combines the floor guard with a narrow low-band veto
exception requiring raw periodicity >= 0.95 and the existing raw zero-crossing
check. On paired pitch-valid tagged frames, median/p90 errors were:

| Clip | Frames | Baseline cents | Experimental cents |
| --- | ---: | ---: | ---: |
| 0001 | 464 | 35.704 / 82.280 | 17.738 / 82.591 |
| 0002 | 1152 | 74.936 / 97.021 | 38.492 / 97.029 |

Vowel frame acceptance changed 693/1281 to 1165/1281 for 0001 and 574/1232
to 1025/1232 for 0002. Sibilant acceptance changed 8/236 to 11/236 on 0001
and remained 0/67 on 0002. On Hook 2 both baseline and this experiment had
43 target commits; this does not prove output transition quality. Key/scale
live-path test passed. P90 did not improve consistently, and no independent
holdout, perceptual listening, instrumented Artist provenance or live-device
qualification was completed. Therefore it is not a release candidate.

The candidate was reverted from the experimental source. Its minimal DSP
diff is preserved as `experimental_periodic_guard.patch` (verified with
`git apply --check` against this source); this patch does not update the
forensic reject-mask telemetry and should not be treated as a production fix.
No installed plug-in was touched.

## Re-entry hold sweep — candidate 5 ms

The renderer waits after an invalid-to-valid control handoff before allowing
wet grains. This protects against clicks but can leave audible dry material
after tracking has already recovered. With the periodic low-band/floor guard
held constant, 12 ms was compared with 8, 6, 5, and 4 ms. The 5 ms candidate
was the local balance on the hard glissando clip 0002:

| Hold | Tagged frames | Median cents | P90 cents |
| ---: | ---: | ---: | ---: |
| 8 ms | 1134 | 33.317 | 96.985 |
| 6 ms | 1135 | 29.546 | 96.662 |
| 5 ms | 1138 | 28.549 | 96.540 |
| 4 ms | 1140 | 28.549 | 96.680 |

On the independent Control_Group clip 0002, 5 ms measured 10.412 / 69.180
median/P90 cents, compared with 10.498 / 70.470 at 8 ms and 10.458 / 69.301
at 6 ms. On Glissando_Group clip 0001 it measured 17.286 / 83.115 versus
17.793 / 82.776 with the original 12 ms guard. Thus the worst-tail metric
is not uniformly better across every clip.

The 5 ms candidate passed `VibeAutotuneKeyScaleLivePathTest`,
`VibeAutotuneCausalTDPSOLATest`, and `VibeAutotuneLiveControlPipelineTest`.
Hook 2 had the same event-log counts as the baseline in the diagnostic
configuration (49 target commits and 3 dry/wet-ramp events). At blocks 32,
64, 128 and 256, Control_Group 0002 rendered identical diagnostic WAV
samples. These checks do not replace perceptual click testing, CPU stress,
other singers, or device qualification. The candidate remains uninstalled.

### Follow-up: held-out control clips and block-size invariance

Two Control_Group recordings of the same singer/song were not used to choose
the guard. On identical paired pitch-valid frames against the historical
Artist bounces, median/p90 absolute error in cents was:

| Clip | Paired frames | Baseline | Guard candidate |
| --- | ---: | ---: | ---: |
| 0001 | 4097 | 14.05 / 62.99 | 9.31 / 48.48 |
| 0002 | 3981 | 21.95 / 83.77 | 10.56 / 72.23 |

This is a useful within-singer holdout, not a different-voice generalisation
test. Control clip 0002 was rendered at host blocks 32, 64, 128, and 256;
the resulting 16-bit diagnostic WAV samples were exactly equal. This shows
block-size invariance for this file and harness configuration, not CPU safety,
device latency, or host-wide equivalence. `compare_guard_holdout.py` performs
the paired comparison while temporary renders exist.

Earlier interpretation correction: `rendererArtifactDryVeto` in this source
only sets a diagnostic flag; it does not force dry. For 0002 between 5.1 and
5.9 seconds the candidate's trace shows actual dry conditions including
invalid source control and the existing 12 ms safety reentry hold. No causal
claim about which one dominates the audible difference is yet established.

Scope: experimental `crossing24-bounded-preview` VST3, F Natural Minor,
Alto, retune/flex/humanize/vibrato zero. This is not an installed or promoted
build. The previously captured Artist reference did not record its binary hash
and exact parameter readbacks; it cannot be a release gate.

## Host/diagnostic equivalence

The diagnostic was built from the candidate's cached source and compile flags;
only its standalone test harness was modified to permit a key index override.
After gain-matching diagnostic mono to the hosted VST3 bounce, normalized RMS
residual was 0.000356 for clip 0001 and 0.000254 for clip 0002. The gain is
approximately 0.7071; this is consistent with a host pan/gain difference, not
by itself proof of its implementation. This validates waveform correspondence
for these two renders, not full host/plug-in equivalence under all conditions.

## Annotated glissando windows

For clip 0001, Vibe diagnostic `voiced=1` for 396 of 1140 trace rows and
`correctionIsActive=1` for 390. For clip 0002, the corresponding counts are
659/2587 and 714/2587. A separate raw-input autocorrelation F0 analyzer returned
finite, confidence >= 0.55 estimates for 511/570 and 1293/1293 frames in the
same tagged windows, respectively. The analyzers use different windows,
thresholds, and timestamps, so these are not equivalent voice-truth labels.

This makes the voiced-evidence / renderer-control handoff a focused hypothesis;
it does not prove why Vibe rejected frames. `voicedEvidence` contains several
conjunctive criteria, and none of their individual reject reasons was captured
in this run. Do not relax tracking thresholds or bypass protections from these
aggregates alone.

## Required next gate

Instrument diagnostic-only per-frame reject reason bits and align them to the
raw annotation and renderer timeline. Compare same-build output with host,
then test one narrowly scoped candidate against these clips, their controls,
Hook 2, and a held-out singer. No production promotion until safety, audio
quality, Artist parameter/provenance, CPU and live-device tests pass.

## 2026-10-17 scoped guard follow-up

Diagnostic-only results narrowed the candidate to two changes: (1) allow the
low-band veto only to be bypassed when raw periodicity is at least 0.95 and
the existing raw zero-crossing guard passes; (2) stop a rejected frame from
training the noise floor only when it is both low-band-rejected and strongly
periodic. This avoids changing normal breathy frames that already pass the
low-band test. The wet re-entry hold was independently narrowed from 12 ms to
5 ms after a 4/5/6/8 ms local sweep.

| Material | Baseline median / P90 cents | Scoped candidate median / P90 cents |
| --- | ---: | ---: |
| Glissando 0001 tagged | 35.247 / 82.672 | 12.635 / 78.942 |
| Glissando 0002 tagged | focused baseline differs* | 26.766 / 96.714 |
| Breathy 0001 all | 5.284 / 23.598 | 5.284 / 23.598 |
| Glissando control 0002 | 235.188 / 1012.788 | 10.690 / 69.856 |

`*` The historical focused baseline used a different valid-frame population,
so it is not a strict paired delta. The scoped candidate passed the key/scale
live-path, causal TD-PSOLA renderer, and live-control pipeline tests. It has
not been installed. It remains an experimental candidate: no cross-singer
dataset, reference plug-in hash/settings audit, CPU stress or physical live
device qualification has been completed.

## Scoped candidate: six-clip paired A/B

The scoped 5 ms candidate was rendered again through the same diagnostic host
as a freshly rendered baseline, then compared only at pitch frames valid in
both variants. Results were written to
`/private/tmp/gtsinger-scoped-matrix/candidate-vs-baseline.csv`.

| Group | Paired result, baseline → scoped candidate (median / P90 cents) |
| --- | --- |
| Breathy Control | 4.976 / 20.934 → 4.976 / 20.934 |
| Breathy tagged | 5.284 / 23.598 → 5.284 / 23.598 |
| Glissando Control | 14.149 / 61.649 → 8.737 / 48.211 |
| Glissando full | 19.691 / 74.620 → 17.257 / 73.318 |
| Glissando tagged | 34.923 / 83.214 → 12.582 / 78.906 |
| Vibrato Control | 3.744 / 43.134 → 3.744 / 43.134 |
| Vibrato tagged | 5.953 / 28.247 → 5.953 / 28.247 |

This is the first measured candidate in this investigation that improves the
targeted glissando measures while producing no measured change in the breathy
and vibrato paired sets. It passes the three focused unit tests described
above and has exact diagnostic WAV equality across blocks 32/64/128/256 for
one control clip. It remains an offline candidate, not a production promotion.
