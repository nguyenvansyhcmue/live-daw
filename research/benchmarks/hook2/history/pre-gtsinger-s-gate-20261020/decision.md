# Pre-GTSinger consonant boundary gate probe

Parent: the selected, isolated Pre-GTSinger `crossing24` app. The research
candidate changed only `CausalTDPSOLARenderer::prepareOutputRenderState` so
the block-RMS-dependent `unvoicedBurstGainTarget` stays at unity. It did not
change F0 detection, note choice, renderer cadence, wet/dry crossfade, or any
public knob. No installed plug-in or listening app was replaced.

The parent code has two separate handoffs: an equal-power wet-to-latency-
aligned-dry fade (7 ms release), and a second unvoiced burst gain (up to
6 dB attenuation, 1 ms attack/20 ms release) that may still affect dry
consonants. Turning off the latter tests only that hypothesis; it does not
establish that this is the user's audible click.

The candidate VST3 built and rendered Hook 2 (Alto/F# Natural Minor) and
GTSinger EN-Alto-2 Breathy/A Thousand Years/0000 (Alto/C Natural Minor),
0/0/0/0. On the three annotated S endings in the latter file, the maximum
single-sample step in a ±30 ms window after adding 1152 samples of plug-in
delay was:

| S ends (raw seconds) | Parent | No-burst-gain candidate |
| ---: | ---: | ---: |
| 3.720 | 0.00062 | 0.00123 |
| 4.801 | 0.01800 | 0.01800 |
| 9.331 | 0.01148 | 0.01737 |

These are not perceptual click scores, but the proposed removal does **not**
reduce the measured boundary peaks and raises two. Reject the no-gate
candidate. Keep the selected Pre-GTSinger app byte-for-byte unchanged.

The earlier 0.1–0.4 dB S-prominence result was measured from a different
installed VST3, not proof that a successful S-boundary fix can be transplanted
into this Pre-GTSinger renderer. To diagnose this exact complaint, obtain the
user's affected bounce (or a 3–5 s crop) and a timestamp, then compare its
wet/dry, gain and F0 transitions with the same audio input and settings.
