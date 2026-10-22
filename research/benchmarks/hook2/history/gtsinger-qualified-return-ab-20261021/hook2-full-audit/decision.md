# Whole Hook-2 audit, 21 October 2026

**Verdict: not fully matched to Artist.** This compares the selected-app-equivalent Vibe bounce and the uninstalled crossing-gated research bounce against the pinned Artist reference. Input is `hook2_raw_segment.wav`; settings are Alto, F# Natural Minor, Retune/Flex/Humanize/Natural Vibrato = 0. No app or plug-in was installed or modified.

The complete raw recording is 11.0345 s. This audit measures 6,832 jointly voiced F0 frames using 1,024-sample windows, 64-sample hops, confidence >=0.55, and a nearest-frame raw-clock join no farther than 128 samples. Breath/noise and low-confidence frames are outside the F0 percentages. The two Vibe bounces have the same measured 1,461-sample envelope offset in this audit; the pinned Artist reference has 83 samples. These are alignment offsets for this particular pair of files, not a claim about real-time latency.

| Whole voiced Hook 2 | Selected app equivalent | Research crossing gate |
| --- | ---: | ---: |
| Median absolute F0 error | 4.456 cents | 4.440 cents |
| P90 absolute F0 error | 23.628 cents | 23.292 cents |
| Rounded-note match | 94.731% | 94.760% |
| Mismatching voiced frames | 360 | 358 |

This stricter nearest-frame calculation differs slightly from the earlier interpolated report (94.46→94.49% match, 24.24→23.86-cent P90), but both methods agree on the conclusion: the candidate improves Hook 2 slightly, not completely. The candidate changes audio chiefly after 4.769 s through roughly 5.408 s, and again near 9.637–9.662 s. It does not repair the earlier 4.217–4.266-s difference.

Per-second note agreement is lowest at 6–7 s (85.45%, but only 213 jointly voiced frames), 4–5 s (88.91%, 631 frames), and 8–9 s (89.70%, 699 frames). At 4–5 s the research candidate lowers median error from 7.74 to 7.02 cents, but note agreement remains 88.91%. At 8–9 s both Vibe bounces are identical under this setting; the candidate does nothing there. The largest continuous rounded-note disagreement found by this estimator is 4.217–4.266 s, around 49 ms, and it is unchanged. Other short disagreement clusters occur around 2.000–2.024 s and 8.177–8.201 s. These are *F0-analyzer leads*, not independently listened-to proof of incorrect musical notes: mixed harmonics, low voiced confidence around boundaries and the Artist renderer can bias an autocorrelation estimator.

The Artist file is mono; both Vibe files are stereo with sample-identical L/R channels. Vibe's per-channel RMS is about 3 dB below Artist/raw throughout the song. The StudioForge host applies equal-power centre pan (`TrackMixing.h`, cos(pi/4)=sin(pi/4)=0.707) to its stereo track, so this fixed level difference cannot be attributed to Vibe DSP from these files. Level-match before listening A/B. The relative 6–10 kHz band fraction varies by section (e.g. selected Vibe about -1.13 dB at 3–4 s and -0.67 dB at 8–9 s); the 6–7-s interval contains little confidently voiced material and must not be called a formant defect without focused listening. This audit does not establish matching formants, consonants, envelope dynamics or absence of clicks.

Inputs, method and exact frame data: [`../analyze_hook2_full.py`](../analyze_hook2_full.py), [`alignment.json`](alignment.json), [`summary.csv`](summary.csv), [`frame-errors.csv`](frame-errors.csv), [`level_spectrum_bins.csv`](level_spectrum_bins.csv). The selected app VST3 remains SHA-256 `617682fa530632e3418793eb3cfb733b2a1359f36082672ce9237440935fbd20`; the research branch is not promoted.
