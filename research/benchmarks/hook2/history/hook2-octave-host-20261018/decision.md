# Octave confirmation experiment: host A/B decision

Research build only; nothing installed. Both VST3 binaries share the same flags except `VIBE_RESEARCH_OCTAVE_CONFIRM_HOPS=12` versus the default 24. StudioForge host rendered Hook 2 with Alto / F# / Natural Minor. Retune 0, Flex 0, Humanize 0 and Natural Vibrato 0 were compared to the archived Artist reference.

* The two Hook 2 case-0 WAVs are byte-identical (SHA-256 `8f3540864b508fd9aac3eba43943c84a52b666e7af3fbd59dd75e80649a27045`). The hard-tune pitch median deviation from the reference was 21.13 cents for both; Artist/Vibe transition counts were 27/25 under this analyser. No improvement on the principal target is demonstrated.
* On the matched Tenor vibrato sample, median deviation changed from 16.76 to 16.59 cents, with 85/67 reference/candidate transitions for both; paired control stayed 5.53 cents and 48/37 transitions. This is small, sample-specific evidence, not proof of audible equivalence.
* In generated 220→440 Hz octave-jump testing at 48 kHz / 64-sample block, capture went from 4000 samples to 2464 samples. The diagnostic prints measurements and exits successfully; it is not a complete automated pass/fail qualification.
* Missing-fundamental and weak-fundamental test cases remained at 23 octave-error observations out of 23 voiced block observations with either setting. Shorter confirmation does not repair the initial detector ambiguity. This test reports observations at the tested block size, not independent audio frames.

Decision: do not promote 12-hop confirmation as a fix for Hook 2. It is still unqualified for false-harmonic rejection and live use. Preserve the production default; investigate the Hook 2 selected-target → actual output error directly with matched timing and reference rather than further changing this threshold. The quality objective is not yet reached.

## Host trace caveat

The subsequent `traced` case-0 bounce, with host trace capture enabled, did **not** match the `baseline` bounce byte-for-byte (SHA-256 `67afb14e196c0aa13d70a44f0eead2f96447c3d0896f4e1cdc63dd2cb6fe43f1` versus `8f3540864b508fd9aac3eba43943c84a52b666e7af3fbd59dd75e80649a27045`). The difference RMS was approximately 0.0255% of baseline RMS over the full stereo file, with a larger isolated peak. This establishes a discrepancy, not its cause. Trace data must not be treated as a sample-exact explanation of that baseline until reproducibility and the capture path have been investigated.
