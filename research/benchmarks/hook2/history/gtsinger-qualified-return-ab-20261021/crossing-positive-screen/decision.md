# Independent crossing-gate screen (21 October 2026)

**Decision: no production promotion.** This is a screen for a second positive activation, not an Artist A/B or a listening qualification. No installed plug-in or DAW app was changed.

The same StudioForge calibration host rendered the same research VST3 (`7a7d3aa7a7e77bf7f0b07278246a296ac16629341943436999be884a2829b40d`) twice per clip. Baseline disabled the diagnostic attack/return flags; candidate enabled qualified attack (10 ms), phase payback, qualified return (7 ms) and `VIBE_DIAGNOSTIC_REQUIRE_PRIOR_CROSSING=1`. Both paths used the same voice, key and scale within each pair, at all 24 control combinations. The zero-control case has Retune/Flex/Humanize/Natural Vibrato all at zero.

| Independent raw clip | Voice; key/scale | Different candidate WAVs / 24 |
| --- | --- | ---: |
| Tenor `All I Ask`, Glissando 0002 | Tenor; F# Natural Minor | 0 |
| Tenor `All I Ask`, Glissando 0003 | Tenor; F# Natural Minor | 0 |
| Alto-2 `A Thousand Years`, Glissando 0001 | Alto; F# Natural Minor | 0 |
| Alto-2 `A Thousand Years`, Glissando 0002 | Alto; F# Natural Minor | 0 |
| Alto-1 `god is a girl`, Glissando 0003 | Alto; C Major | 0 |
| Alto-1 `god is a girl`, Glissando 0001 | Alto; E Major | 0 |

All 144 paired WAV files are byte-identical (not just equal at the F0 analyzer's resolution). The latter two clips were selected from note annotations because they contain low-note → adjacent-up → return gestures; their score annotations do not establish that the renderer's prior-crossing condition occurs. The C/E key assignments allow the annotated adjacent notes in the selected scale. Artist was **not** newly rendered for these six clips because the candidate made no audible-data change to compare.

Together with the 288/288 original-key GTSinger null results and the independent Tenor F# null, the new gate has avoided known collateral changes but has **not** shown positive transfer beyond Hook 2. It may be too restrictive, or the independent clips may lack the exact causal state; these null tests cannot distinguish those explanations. Do not weaken a threshold or hard-code a song event to force an activation. The next useful step is to instrument the gate's prerequisite states on labelled independent phrases, then obtain an Artist render only if an eligible phrase actually changes and passes a basic click/level check.

The selected listening app's embedded VST3 remains SHA-256 `617682fa530632e3418793eb3cfb733b2a1359f36082672ce9237440935fbd20`. The research VST3 remains separate and uninstalled. Reproduction command: `zsh artifacts/gtsinger-qualified-return-ab-20261021/screen_crossing_holdouts.zsh` for the first four clips; the last two were rendered with the same runner and flags, using C Major and E Major respectively. Each pair's `runner.log` and 24 WAVs are in this directory.
