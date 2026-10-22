# macOS virtual-input device — Phase 03 foundation

`macos/StereoLoopbackRing` is the fixed-size PCM transport for the first
endpoint: interleaved Float32 stereo, one HAL output-stream writer and one HAL
input-stream reader. It is allocation-, lock- and wait-free while either stream
is running. Overload rejects newest frames; an input underrun is explicitly
zero-filled. Its focused test uses actual stereo PCM samples, wraparound,
overflow, underrun and stop/clear behavior.

`macos/VirtualInputFormat` is the matching first-release negotiation contract:
interleaved 32-bit float stereo at 44.1 or 48 kHz with 64–1024 frames per
buffer. Unsupported mono, multichannel, non-float, non-interleaved, out-of-
range buffer sizes and sample rates are explicitly rejected. The HAL property
layer must publish and enforce this same contract.

This is **not** a mock device. It builds as a signed `.driver` bundle and can be
staged into a guarded `.pkg`, but it is not installed or production-verified.
A real macOS Audio Server Plug-in is hosted separately from the DAW. The
production boundary is therefore:

```
StudioForge audio engine -> Core Audio client writes virtual device output
HAL Audio Server Plug-in: bounded loopback transport
external recorder opens virtual device input -> receives PCM
```

The plug-in must expose a paired stereo Float32 stream at a negotiated sample
rate/buffer size and implement HAL start/stop, format and device lifecycle
properties. Its `DoIOOperation` path is where this ring is used. It must not
call the DAW, allocate, lock or perform IPC synchronously on that callback.
The first endpoint deliberately supports one recording consumer; additional
independent readers require a separate cursor per consumer and are out of scope
until the first endpoint is verified.

## Installation gate

The actual HAL bundle must be release-signed, installed by an administrator in
`/Library/Audio/Plug-Ins/HAL/`, and then validated in Audio MIDI Setup and a
separate recording app. `Tools/build_macos_link_installer.sh` creates the
guarded installer but never runs it or restarts audio services. No endpoint is
claimed until installation/reboot/verification happen. The repository does not copy a
third-party virtual driver; its license and signing process must be reviewed
before any external driver code is adopted.

Apple's supported Audio Server Plug-in guidance and install location are here:
https://developer.apple.com/documentation/coreaudio/creating-an-audio-server-driver-plug-in
