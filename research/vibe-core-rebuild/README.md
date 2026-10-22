# Vibe core rebuild — research build, NOT a production release

Status: new single-path DSP compiles and renders through StudioForge. The
listening/transition/latency gate is NOT passed. No DAW/app or installed plug-in
was replaced. Do not identify this directory as the approved listening version.

## Architecture

`Input → timestamped F0/voicing → retained musical policy → new control trajectory
→ LPC inverse filter → fractional residual shifter → LPC synthesis filter
→ output`

Unvoiced blending happens in excitation space, with a continuously running
synthesis filter. There is no old renderer switch. The two fractional read heads
are components of ONE residual shifter, not two product engines. A non-finite/
extreme-value guard returns delayed input and increments a failure counter;
this is an emergency fault handler, not a legacy renderer fallback.

The design is an original prototype, not a reconstruction of Antares' code.
No decompiled code or new GPL DSP dependency was used. Existing JUCE licensing
requirements still apply. Public source/filter background:
[LPC analysis and synthesis](https://ch.mathworks.com/help/dsp/ug/lpc-analysis-and-synthesis-of-speech.html).

## What is actually changed

All replacement source is here, inside the writable workspace. The canonical
`/Users/hiimdrdey/code/daw` is READ-ONLY in this session and has extensive user
changes. **Its old DSP files have NOT been deleted or replaced.** This is a
remaining migration blocker, not completed cleanup.

Replacement boundary:

| Original DSP component | Replacement in this source tree |
|---|---|
| `SignalsmithPitchRenderer`, `BufferedSpectralPitchRenderer` | No import, include, dependency or runtime branch |
| `CausalTDPSOLARenderer`, `EventOwnedSpectralFrameQueue` | No import, source-mark/epoch queue or grain scheduler |
| `CorrectionTrajectory`, `LiveControlPipeline`, `NoteTransition` | New `ControlTrajectory`; only unchanged musical selection functions extracted |
| `PitchDecomposer`, `HumanizeProcessor`, `VibratoProcessor`, `VoicedColourProcessor` | New observer/trajectory/source-filter implementation |
| Old `PluginProcessor.cpp/.h` | New processor wrapper plus `FrozenContract.cpp` |

Unchanged: UI source/assets, `NotePolicy.h`, scale data, nearest/directed target
selection, parameter declarations and state serialization. Six diagnostic-only
parameter IDs remain inert compatibility reservations in the frozen declaration;
their old algorithms are absent. This is an explicit cleanup exception to avoid
silently changing the published parameter contract, not a claim that those knobs
still perform calibration. Public four-knob behaviour has basic tests but has
NOT yet been fully recalibrated against Artist.

No research source, audio references, user projects, old app or git history was
deleted. No changes were made to installed Artist/Vibe.

## Build and verify

The local JUCE and StudioForge paths are explicit CMake inputs; this is not yet
a portable, standalone DAW checkout. Use the pinned JUCE already present locally.

```sh
cd /Users/hiimdrdey/autotune/vibe-core-rebuild
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --target VibeAutotune_VST3 VibeAutotune_AU VibeCoreTests VibeContractTests VibeRenderTrace StudioForgeReferenceRunner -j 4
python3 tools/import_frozen_contract.py --check
ctest --test-dir build --output-on-failure
```

The reference runner uses StudioForge's actual `AudioEngine`, graph and plugin
host source. It is not an independently invented render loop. The separate
`VibeRenderTrace` diagnostic is null-checked against that host after its pan-law
gain, to establish whether instrumentation is measuring the same synthesis.

Read [DECISION.md](DECISION.md) before any packaging. Current build is for
Studio-quality research only: algorithmic latency is 1780 samples at 48 kHz,
not below 5 ms. Hardware roundtrip and live CPU qualification are not measured.

## Next engineering gate

1. Resolve canonical workspace write access before attempting source migration;
   enumerate exact files and preserve the current UI/host modifications.
2. Verify fresh Artist AU registration and readback of all settings in the same
   host process; do not fit against the questionable F/F# archived reference.
3. Examine raw F0 → selected target → requested ratio → output pitch around
   adjacent glides across Hook 2 and independent clips. The new first ascent is
   too abrupt; adding a global smoothing constant is not justified.
4. Qualify onset/F0-loss/reacquisition and anti-phase/stereo input behaviour,
   sample-offset MIDI/automation, clicks under automation, and all four knobs.
5. Blind/level-matched listening for doubled voice/formant artefacts, including
   /f/ and /sh/ with reliable labels. Spectral proxies cannot pass this gate.
6. Only then install/package one canonical product; no legacy DSP in that build.
