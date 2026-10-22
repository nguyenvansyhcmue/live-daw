# MXTune → Vibe renderer: feasibility gate (2026-10-22)

## Verified source facts

- MXTune defaults to `DETECTOR_TYPE_YIN_FAST` and `SHIFTER_TYPE_SOUND_TOUCH`, not a phase vocoder. Its `mx_tune::run` calls detector, target update, shifter and delay per input sample. It has selectable alternatives, but the repository does not establish a lock-free parallel `processBlock` architecture for its default path. [MXTune source](https://github.com/liuanlin-mx/MXTune/blob/master/mx_tune.cpp)
- MXTune attributes its core algorithm to Autotalent and labels the repository GPL-3.0 with additional component licenses. Do not copy its source into a differently licensed product without reviewing obligations. [README](https://github.com/liuanlin-mx/MXTune), [license](https://github.com/liuanlin-mx/MXTune/blob/master/LICENSE)
- The exact-host Vibe snapshot selected for listening sets TD-PSOLA latency to 1152 samples (24.0 ms at 48 kHz) and feeds the same delay to host PDC and the renderer's control stream. The associated Alto research build uses a 1024-sample pitch-analysis frame and a 128-sample hop. [local processor](artifacts/crossing24-bounded-preview-20261017-112706/source/VibeAutotune/PluginProcessor.cpp)
- The current DAW source does **not** contain a universal 8 ms one-pole output smoother as asserted in the request: the normal renderer dezipper constants are 6 ms and 32 ms, interpolated by Retune, and explicit hard-tune uses 0. Preserve actual behaviour, not an assumed constant. [local DAW processor](/Users/hiimdrdey/code/daw/autotune/VibeAutotune/PluginProcessor.cpp)

## Latency / quality conflict

At 48 kHz, a 5 ms plugin latency budget is 240 samples. A Bernsee-style STFT with 256-sample window / 64-sample hop retains 192 samples (4 ms) of input/output FIFO delay **before** tracker/target decisions; a 512/128 setting already retains 384 samples (8 ms). An N=256 FFT has 187.5 Hz bin spacing at 48 kHz and cannot by itself provide a reliable vocal harmonic/formant envelope across an Alto's low range. This does not prove every possible pitch shifter exceeds 5 ms, but it rules out guaranteeing the requested high-quality STFT + robust low-note analysis + existing target timing under 5 ms without measurement or a significant quality compromise. Even Rubber Band's dedicated real-time, formant-preserving shifter documents 50 ms or more depending on configuration. [Rubber Band LiveShifter](https://breakfastquay.com/rubberband/code-doc/classRubberBand_1_1RubberBandLiveShifter.html)

COLA is necessary for overlap gain under the chosen window/hop and normalization; it is **not** sufficient to remove pitch-change smearing, phase discontinuity or formant coloration. LPC also cannot promise perfect formant preservation; it needs independent voiced/unvoiced, stability and artifact qualification.

## Decision before implementation

Recommended: retain and freeze the approved Live path; build a **separate, opt-in Studio spectral renderer** behind the existing target-ratio interface, with preallocated per-instance FFT/rings, coherent synthesis phase, measured WOLA normalization, controlled dry alignment, and A/B/trace parity. Promote only after artifact, CPU, latency and holdout tests pass. Replacing the only renderer in production would discard the selected no-harmony listening baseline before the alternative is qualified.

If a strict sub-5-ms *plugin* target is mandatory, it needs a separate low-latency design/quality contract and explicit device-roundtrip definition. It cannot be promised by selecting MXTune or by switching to STFT. If a strict sub-5-ms *end-to-end* live monitoring target is meant, include interface input/output buffers and host scheduling; the current processor alone reports 24 ms.

No DSP, installed VST3, DAW package, control mapping or trace path was changed in this audit.
