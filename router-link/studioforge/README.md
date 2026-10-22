# StudioForge DAW integration audit — Phase 04

## Actual ownership (do not duplicate it)

`TrackDataModel` owns tracks, sends, aux returns, their FX racks and persisted
routing state. `AudioEngine` owns the device callback and existing `AudioGraph`.
StudioForge Link must not replace either. Parameter/macro control stays in
`Control/`, separate from PCM transfer.

The audited live PCM path already present in the DAW is:

```
microphone -> renderInputMonitoring -> track FX (including VibeAutotune)
           -> track/aux/master graph -> processingBuffer
           -> physical Master outputs 1/2                 (monitor path)
           -> streamBusBuffer -> publishStreamOutput
           -> StreamOutputBridge -> selected secondary output device
```

The branch begins after master processing and writes preallocated buffers only;
it does not add a processor or latency to microphone monitoring. The physical
path can still be panic-muted independently. `closeStreamOutputDevice` removes
the published bridge before stopping the device and retains old bridge storage
until shutdown, preventing a callback pointer-lifetime race.

Once the real StudioForge Link virtual device is installed, select it through
Device Settings **Stream Output**. The DAW then writes to the virtual device as
a Core Audio client; its HAL input becomes the recording endpoint. No second
DAW process or duplicate routing graph is needed.

## Required workflows: implementation status

| Workflow | Existing supported route | Status |
|---|---|---|
| Mic -> Vocal DSP -> Live -> virtual endpoint | Existing input monitoring, FX and stream branch | Code path ready; OS endpoint awaits Phase 03 HAL install |
| Monitor bus -> physical interface | Primary `AudioEngine` callback outputs 1/2 | Implemented; no Link dependency |
| Music bus -> AutoKey | `liveKeyReferenceBuffer` and `LiveKeyDetector` from explicit reference track | Implemented; no Link dependency |
| External application -> Music Bus | No process-capture input/device client route exists | Not implemented |

`getAvailableAudioOutputDevices`, `getStreamOutputDevice`,
`isStreamOutputConfigured` and `getStreamPeak` expose availability and stream
state. A selection is connected only after its callback begins; device loss
clears configured state.

## Verification boundary

The DAW and focused Link tests compile, but end-to-end verification requires a
signed installed HAL endpoint and external recorder. The current environment
cannot write the HAL install directory and exposes no visible Core Audio device,
so Phase 04 is **PARTIAL/BLOCKED** for the real endpoint. A mock device or a
fictional external-app Music Bus route would be misleading and is not added.
