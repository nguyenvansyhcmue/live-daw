# Annotated independent-singer fricative check

GTSinger EN-Alto-2, Breathy / A Thousand Years / Control_Group / 0000;
annotated TextGrid phone tier; Alto / C Natural Minor / 0/0/0/0. The Artist
reference is the existing 20261018-051314 host render. `current-candidate`
is a fresh render of the previously rejected output-time + gate + high-band
research snapshot, not the installed production VST3. A separate prior
`gtsinger-holdout-downward29.7DMqwy` render was also measured. These two
research builds are not an installed-plugin A/B and cannot prove production
behavior. Data are internal research only; audio has not been redistributed.

The measurement script fits one high-pass (>5 kHz) waveform delay per full
annotated phone interior (excluding 15 ms at both ends), not a separate lag
per onset window. A synthetic delayed and gain-scaled noise test recovered
1152 samples and correlation > 0.999999. This does not establish annotation
accuracy or perceptual quality.

Three annotated S interiors had Artist/raw correlations 0.907, 0.985 and
0.811 and Vibe/raw correlations 0.999, 1.000 and 0.997. Artist fitted delays
were 2629, 2765 and 2726 samples; Vibe was 1152 in all three. Since search
was conducted independently, correlations are not evidence of identical
algorithm or sample-accurate onset. The F interval had Artist/raw correlation
only 0.534 and cannot support a firm conclusion about its alignment.

One global RMS gain per full file was used by the CSV: Artist 1.41490 and
candidate Vibe 1.65883 relative to raw. Under that normalization, S interior
high-band Vibe minus Artist was +1.664, +1.429 and +1.549 dB. However these
two global multipliers themselves differ by 1.382 dB. If the same gain is
instead applied to both host stereo outputs, the three interior differences
are about +0.282, +0.048 and +0.167 dB. Neither choice determines subjective
brightness: overall output gain differs, and loudness matching policy must be
specified and verified. Do not infer a 1.4 dB DSP defect from the normalized
figures alone.

Using those single phone-interior delays and identical gain for both plugin
outputs, 20 ms high-band onset windows for the three S annotations differ
from Artist by +0.24, -1.35 and -0.71 dB at their marked starts, and +0.35,
-0.07 and -0.22 dB 20 ms later. TextGrid boundaries may not coincide with
physical onset, and the interior delay may not remain valid at onset. These
are exploratory landmarks, not proof of an onset defect.

Decision: on this one additional singer, the clear S interior resembles raw
and Artist closely after accounting for host gain; no new DSP change is
justified. More voices, consistent gain policy, human listening and checking
the actual installed binary are required. Preserve the failed trials for
reproducibility, keep them uninstalled, and do not claim Artist equivalence.

## Updated local-level policy and installed-binary verification

The measuring tool now uses the median of overlapping 20 ms RMS ratios from
the labelled preceding vowel, and reports its IQR. It also reports high-band
fricative prominence relative to that vowel inside each renderer. This avoids
whole-file RMS normalization; a synthetic delayed-noise test validates delay
recovery, and helper tests validate ARPAbet vowel selection. It does not turn
TextGrid timestamps into ground-truth acoustic onsets.

The installed VST3 was rendered again under the same Alto/C Natural Minor
fixture. The three usable S phones were +0.354, +0.105 and +0.304 dB more
prominent than Artist relative to their preceding vowels; the associated
vowel-gain IQRs were 0.310, 0.253 and 0.044 dB. The much larger +5.60 dB
result belongs to the rejected research snapshot, not the installed VST3.
This is evidence against a large repeatable installed-plugin sibilance defect
on this clip, not proof that no user-recording issue exists.

A second independent fixture, EN-Tenor-1 Breathy / All I Ask / Control_Group
0000, was rendered through that same installed VST3 with Tenor/C Major. Its
one usable annotated S had Artist/raw correlation 0.925, Vibe/raw correlation
~1.000, preceding-vowel gain IQR 0.644 dB, and Vibe-minus-Artist sibilance
prominence +0.400 dB. This is consistent with the Alto range (+0.105 to
+0.354 dB) but is only two clips and four usable S phones total.

Practical consequence: do not introduce an aggressive consonant gate or
high-band handoff based on the failed research candidates. The next issue to
measure should come from a reproducible user hearing test or a larger
annotated corpus, then use this phoneme-local metric as a regression gate.
