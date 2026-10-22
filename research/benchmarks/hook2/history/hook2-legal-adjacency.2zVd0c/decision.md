# Hook-2 hard-tune decision — verified fixture

## Fixture

- Raw: `source/renders/hardlock-pulse-anchor/hook2_raw_segment.wav`
  (`c241b07c…`, verified in `BENCHMARK_INPUT_PROVENANCE.csv`)
- Target: `source/renders/target-autotune-artist.wav`
  (`fe8fcafac…`, verified in `TARGET_MANIFEST.csv`)
- Host: `StudioForgeCalibrationRunner`; Alto, F# Natural Minor, tracking 50,
  Retune/Flex/Humanize/Natural Vibrato = 0.

The older `hook2-artist-vibe-20261014-041857` artifact is not used as the
target because it has a different output checksum from the verified Artist
target.

## Accepted research champion (not installed)

`VIBE_RESEARCH_LEGAL_SCALE_ADJACENCY=1` with the existing 24 ms predictive
renderer crossing.

| Candidate | F0 median abs error | P90 | P99 | Vibe transitions |
|---|---:|---:|---:|---:|
| Baseline chromatic adjacency | 4.528 cents | 25.325 | 140.006 | 27 |
| Legal-scale adjacency, 24 ms linear | **4.518** | **24.791** | **125.601** | **29** |
| Artist target | — | — | — | 30 |

This change makes C# <-> B in F# Natural Minor eligible for the same
neighbour-note protection as chromatic neighbours. It does not alter the
selected scale; `VibeAutotuneNotePolicyTest` and
`VibeAutotuneKeyScaleLivePathTest` pass with the candidate.

## Rejected branches

- Downward selector holds of 18/29/36 frames: remove genuine short B3 dips.
- 26 or 28 ms crossing: add 2 or 1 transitions respectively and worsen P90.
- Ease-in crossing curves 1.25 and 1.50: add transitions and worsen P90/P99.
- Disable trajectory-preview commit: only improves one local window by 0.56
  cents but worsens global P90 from 24.791 to 28.419 cents.
- Global direct-hard-tune boundary hysteresis: 8 cents repairs the 4.212 s
  mixed-boundary median (95.42 -> 9.14 cents), but P90/P99 become
  26.527/185.371 and transitions fall to 26.  Six cents has the same failure
  mode (26.024/181.041; 24 transitions). It is not a viable global policy.

## Remaining local mismatch

The largest sustained window is approximately 4.212–4.312 s. It includes a
brief voiced/unvoiced boundary: Artist makes a shallow 57->56 dip and returns;
Vibe reaches 56 then loses F0 shortly after. The rejected preview switch did
not materially change this event, so the next investigation must target the
causal detector confidence/re-entry or renderer handoff—not global target
dwell, not Retune speed, and not the four UI knob mappings.

No candidate from this directory is installed, signed, or deployed.
