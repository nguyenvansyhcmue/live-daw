# StudioForge Link — Phase 03 (partial foundation)

The core routes planar stereo PCM. The macOS diagnostic CLI now has an
experimental same-device duplex Core Audio path; hardware operation and
permissions have not yet been verified. The first macOS virtual-device PCM
transport and a loadable macOS HAL bundle are implemented and tested. A
fail-closed `.pkg` release-candidate builder now exists, but no installed-device
verification has been completed on this machine. There is still no Windows
virtual-device backend or signed Windows driver package.

## Ownership and direction

- `core/`: platform-independent bounded stereo routing and configuration.
- `platform/`: experimental macOS Core Audio device I/O; not yet verified.
- `virtual-device/`: bounded PCM transport and macOS HAL driver boundary. The
  bundle/installer can be built, but no endpoint is claimed as system-visible
  until installation, reboot and independent-client verification pass.
- `standalone/`: a minimal command-line device controller on macOS.
- `studioforge/`: future integration with the existing DAW, not a replacement
  for its audio engine. No adapter is implemented.
- `tests/`: focused core tests.

## Core contract

The owner chooses persistent nonzero endpoint IDs and prepared endpoint, route
and frame limits. Sources and destinations connect through optional buses in a
directed acyclic graph. Per-route channel map, gain and mute apply to each
block. Missing input samples are silent; oversize blocks are rejected and the
declared output extent is silenced. Input/output buffers are caller-owned,
non-aliasing and valid for the call. Each destination is copied to each output
block. This synchronous block interface is not an asynchronous clock bridge.

One control thread publishes validated configurations into three prepared
slots; one audio thread adopts the newest configuration at block boundaries.
`process` does not allocate or lock. Construction and destruction require a
stopped callback. Versioned text serialization provides persistence data, but
the owner must store it safely on the control thread. No sample-rate conversion,
device synchronization, interprocess transport or external feedback detection
exists yet. Graph cycle validation cannot detect external application loops.

## Experimental macOS device path

The controller commands are `list`, `start <device-id>`, `status`,
`volume <0..1>`, `stop`, and `quit`. Start is muted for feedback safety.
Only a single available full-duplex device, with matching non-interleaved
Float32 input/output and stereo output, is accepted. No separate input and
output clocks or resampling are supported, and the system default is never
changed. Use headphones: microphone-to-speaker monitoring can cause feedback.
Device IDs are session-local; the reported UID is for identification only.
An unplugged device is reported on `status`; stop and manually select a
reconnected device. Automatic recovery, macOS microphone permission prompting,
and a signed app bundle are not implemented. Start success and callback count
alone do not prove microphone permission or audible output.

Apple's Core Audio process taps require macOS 14.2+, a system-audio capture
usage description and permission; they are not implemented by this CLI. Some
protected audio may be unavailable. See Apple's documentation:
https://developer.apple.com/documentation/coreaudio/capturing-system-audio-with-core-audio-taps

The future platform backend, virtual-device bridge, standalone controller and
DAW adapter may depend on the core; the core must not depend on them or on the
DAW. Concrete APIs and data transfer will be introduced only when a working
audio path is selected and tested. In particular, a driver may live in a
different process or OS component; a C++ library does not by itself provide
shared runtime state across those boundaries.

## Existing DAW integration candidates

`AudioEngine` owns device lifecycle and its audio callback. Its existing
`publishStreamOutput` and stream bus are possible output integration points;
`TrackDataModel` owns track and bus routing. These are candidates, not an
integration promise: the existing stream bridge is stereo and independently
opens a device, so clock drift, sample-rate mismatch and lifetime safety must
be reviewed before reuse. Input to AutoKey must preserve its explicit reference
track semantics. No existing component is modified or linked by this phase.

## Build

From the repository build tree, build `StudioForgeLinkController` and
`StudioForgeLinkSmokeTest` and `StudioForgeLinkRoutingTests`, and run
`ctest -R StudioForgeLink`.
Alternatively configure this directory independently with CMake and run the
same targets and test. The controller is a diagnostic CLI, not a product UI.
