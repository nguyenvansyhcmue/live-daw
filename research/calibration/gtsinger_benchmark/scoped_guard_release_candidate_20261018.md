# Scoped guard — release-candidate record

This record describes an offline source candidate. It is not an installed, signed,
or production-approved plug-in.

## Exact scope

The patch in `experimental_periodic_guard.patch` has exactly three DSP changes:

1. The detector may pass the existing low-band-energy veto only when the raw
   periodicity is at least `0.95` and the existing raw zero-crossing limit also
   passes.
2. A frame rejected solely by that low-band veto cannot train the adaptive noise
   floor when it is already strongly periodic (`>= 0.75`) and meets the existing
   periodicity/correlation requirements.
3. TD-PSOLA wet re-entry safety hold changes from `12 ms` to `5 ms`.

No UI control, voice/key/scale mapping, Retune, Flex-Tune, Humanize, Natural
Vibrato, formant, or public parameter range changes in this candidate.

## Evidence retained

Fresh paired diagnostic bounces at Alto / F Natural Minor / 0-0-0-0 showed:

| Material | Baseline median / P90 cents | Candidate median / P90 cents |
| --- | ---: | ---: |
| Breathy control | 4.976 / 20.934 | 4.976 / 20.934 |
| Breathy tagged | 5.284 / 23.598 | 5.284 / 23.598 |
| Glissando control | 14.149 / 61.649 | 8.737 / 48.211 |
| Glissando full | 19.691 / 74.620 | 17.257 / 73.318 |
| Glissando tagged | 34.923 / 83.214 | 12.582 / 78.906 |
| Vibrato control | 3.744 / 43.134 | 3.744 / 43.134 |
| Vibrato tagged | 5.953 / 28.247 | 5.953 / 28.247 |

The candidate also passed key/scale live path, causal TD-PSOLA renderer, and
live-control handoff tests. A diagnostic control WAV was sample-identical at
32/64/128/256-sample host blocks.

The exact archived candidate was rebuilt as VST3 on 18 October 2026. Its
ad-hoc-signed Mach-O SHA-256 was:

`c877b9ced6df4c1e213adae659d0f40a3d7ba5c7d28416da24145741ddadfb7e`

That checksum identifies a diagnostic artifact only; it is not the binary
currently installed in any host.

## Promotion boundary

The candidate may be rebuilt for controlled listening, but must not be called
"Artist-identical" or become the default live build until all of these are
captured against the exact installed binary:

- Artist reference binary/version and complete parameter readback;
- an independent singer, not only EN-Alto-1;
- real-interface 32/64/128 callback CPU/xrun measurement;
- live voiced/unvoiced, plosive, sibilant, key-change, and disconnect/reconnect
  safety checks;
- ABX listening confirmation that the 5 ms re-entry does not introduce clicks.

Run `verify_scoped_guard_candidate.zsh` with `VIBE_BUILD_DIR` set to repeat the
source and three focused test gates. It deliberately does not install a plug-in.

## Independent-singer gate

The fixture tooling now supports repeatable `--voice` selection and preserves
the dataset singer alongside Vibe's public `Voice` setting in the generated
plan. The current local fixture still contains only `EN-Alto-1`; first acquire
`EN-Alto-2` and `EN-Tenor-1`, generate a fresh plan, and render a fresh Artist
reference for those exact inputs. Historical Artist bounces must not be reused
as if they were a cross-singer reference.
