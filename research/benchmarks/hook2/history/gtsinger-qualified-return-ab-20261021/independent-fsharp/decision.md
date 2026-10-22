# Independent F# minor Artist/Vibe handoff A/B

**Decision: reject the cadence-gated attack as a production promotion on current evidence.** Keep the selected listening app and installed VST3 unchanged.

The user's normal macOS Terminal validated Auto-Tune Artist AU and rendered the independent GTSinger `EN-Tenor-1/Glissando/All I Ask/Glissando_Group/0001.wav` through the StudioForge calibration runner. The Artist run is `../artist-fsharp-terminal.96sIS0`, runner SHA-256 `202e67954f8601becef1e7f5bc73b1fb1255837d5aac0e34988a97f5a4ab5273`, raw WAV SHA-256 `da8b787b06ba2284d224770293c74bcf8c8ec46ec2a4bf05e10b894a00ec24c5`. Artist used `Alto-Tenor / F# / Natural Minor`; Vibe used its corresponding `Tenor / F# / Natural Minor`. Case 0 has Retune, Flex, Humanize and Natural Vibrato all at zero. Both Vibe renders used the same StudioForge host, raw file and research VST3 SHA-256 `5f7aa1becf3367a2a09aea63ff7789580b406f04335ae19f331ec627dee07a33`; only the diagnostic attack/return flags differed. Nothing was installed.

The candidate changed 954 stereo PCM frames only, at Vibe output 2.209146–2.229000 s (raw-clock 2.175208–2.195063 s after subtracting the measured 1,629-sample Vibe delay). The Artist output delay was 2,673 samples. On the 15 jointly voiced 64-sample-hop F0 frames in that 20-ms affected region, the candidate **did not improve Artist agreement reliably**:

| Metric | Baseline | Cadence-gated candidate |
|---|---:|---:|
| Local mean absolute pitch error | 102.079 c | 102.211 c |
| Local median absolute pitch error | 124.073 c | 121.802 c |
| Local P90 absolute pitch error | 127.362 c | 136.345 c |
| 100-ms handoff mean absolute error | 62.088 c | 62.420 c |
| Whole-clip median absolute error | 88.758 c | 88.758 c |
| Whole-clip transition count (Artist 24) | 25 | 25 |

Across the 24 control cases, 22 candidate WAVs differ from baseline. Using a 0.05-cent threshold on whole-clip median F0 error, 3 cases improved, 6 worsened and 15 were within threshold. The changed zero-control region's local RMS was 0.098687→0.098675 full scale and its maximum adjacent-sample step was unchanged at 0.023240; that coarse check is **not** a proof of no click, formant shift or audible artifact.

This is a valid same-input/same-key Artist comparison, but it is **not** a positive transfer fixture for the Hook-2 attack rule. The new 60-cent synthesis-cadence condition still improves the original Hook-2 measurement, but here it activates without a demonstrated pitch benefit and worsens local P90. Do not tune another threshold to this single clip or promote it. Keep the diagnostic branch default-off; next work should identify an event-state discriminator from internal traces across both phrases, then require an additional holdout and listening/CPU checks before any packaging.

Reproduce the F0/continuity numbers with `analyze_hard_zero.py`; the two `calibration-report.csv` files and their `f0-traces` folders preserve all 24 case comparisons. F0 analysis uses 1,024-sample frames and 64-sample hops; the 20-ms result is consequently a coarse windowed estimate, not a sample-accurate acoustic transition measurement.

## Causal crossing discriminator, 21 October (research only)

Exact-host control/epoch/OLA traces were captured for Hook 2 and this Tenor clip. For each, tracing produced a **byte-identical** hard-tune-zero WAV to the earlier untraced candidate. Hook 2's first adjacent rise commits at source sample 227,680, and a certified renderer crossing toward the same note was active through sample 227,648 (32 samples earlier). The Tenor rise commits at sample 104,928, with no such crossing in the preceding captured window. A target change by itself therefore does not identify the same musical handoff in these two clips. This is a difference in Vibe's causal control state, **not** evidence of Artist's internal algorithm.

A second default-off diagnostic gate now requires a recent crossing preview for the same destination, in addition to the existing 60-cent synthesis-cadence deficit and other held-note conditions. This is research source only (`VIBE_DIAGNOSTIC_REQUIRE_PRIOR_CROSSING=1`); it has no song, singer, timestamp or note-number exception. With all diagnostic flags on, Hook 2's all-zero WAV remains byte-identical to the prior improved candidate (SHA-256 `b6961f7327b4418ce564f93330e3def94fbae40442225e450ff5d01c2dd95264`). On this independent Tenor F# fixture, **all 24 WAVs** now null byte-for-byte against baseline; the earlier 954-frame unwanted change is gone.

The full key-aware GTSinger run at [`../crossing-gate-full`](../crossing-gate-full) completed 12 jobs × 24 cases. All **288/288 WAVs** null against their corresponding baseline WAVs under the dataset's original keys/scales, including the 32 nonzero-control differences left by the previous cadence-only gate. The 12 jobs contain only 10 distinct raw WAV hashes, so this is a regression check, **not** 12 independent demonstrations of positive transfer. The same uninstalled VST3 binary, SHA-256 `7a7d3aa7a7e77bf7f0b07278246a296ac16629341943436999be884a2829b40d`, was used; the run manifest does not capture environment flags, which were: `VIBE_DIAGNOSTIC_QUALIFIED_ATTACK_PLANNER=1`, `VIBE_DIAGNOSTIC_QUALIFIED_ATTACK_MS=10`, `VIBE_DIAGNOSTIC_ATTACK_PHASE_PAYBACK=1`, `VIBE_DIAGNOSTIC_QUALIFIED_RETURN_RATIO=1`, `VIBE_DIAGNOSTIC_QUALIFIED_RETURN_DELAY_MS=7`, `VIBE_DIAGNOSTIC_REQUIRE_PRIOR_CROSSING=1`.

With all flags off, the rebuilt binary's 24 Hook-2 WAVs null against the prior baseline. Four focused tests pass: CausalTDPSOLA, CorrectionTrajectory, LiveControlPipeline and KeyScaleLivePath. **Decision remains research-only.** The new condition preserves Hook 2's measured benefit and removes the known negative Tenor activation, but this dataset contains no second *positively affected* crossing fixture with a matched Artist render. No listening, formant, real-device CPU or click qualification was performed. The selected listening app and installed plug-in remain untouched.
