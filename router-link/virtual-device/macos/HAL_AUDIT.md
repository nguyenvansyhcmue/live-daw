# macOS HAL audit — bounded milestone

## M2A.1 driver foundation

`StudioForgeLinkHAL.cpp` now provides a real CFPlugIn factory, driver interface,
one duplex device, one stereo input stream and one stereo output stream.
It reports a stable UID and Float32 interleaved stereo at 44.1 or 48 kHz.
Rate changes use Core Audio's host-negotiated device-configuration handshake
and are applied only while IO is stopped. `WriteMix` now writes
into `HalDuplexLoopback`; `ReadInput` reads matching PCM through independent,
fixed reader cursors. An underrun is zero-filled; overflow rejects newest
frames; writer disconnect increments the timeline so stale audio cannot replay.

This is a buildable/tested loopback driver. The guarded installer RC is produced
by `Tools/build_macos_link_installer.sh`; it is not eligible for public release
until Developer ID signing, notarization and installed-device verification are
complete.

## Safe preflight

Build and run `StudioForgeLinkHalPreflight`. It only reports whether the Core
Audio HAL SDK header is available, whether `/Library/Audio/Plug-Ins/HAL` exists,
whether the current process can write it, and (optionally) whether a candidate
bundle has the basic `Contents` shape:

```
STUDIOFORGE_LINK_HAL_BUNDLE=/absolute/StudioForgeLink.driver \
  ./StudioForgeLinkHalPreflight
```

It never uses sudo, changes the default device, installs files, restarts audio
services, or claims an endpoint is connected.

## Manual installation (only after later verification)

Do not install this incomplete foundation. Once a signed release bundle has
passed loopback tests, an administrator can copy it to
`/Library/Audio/Plug-Ins/HAL/`, then restart normally and inspect it in Audio
MIDI Setup. Removal is the inverse: remove only the exact StudioForge bundle,
then restart normally. This build never uses sudo, changes default devices, or
restarts Core Audio.

## Required next bounded implementation

1. Verify the same path through an installed macOS HAL endpoint with independent
   Core Audio playback and recording clients.
2. Build/sign the `.driver`, then have an administrator install it into the
   system HAL directory and verify Audio MIDI Setup plus an independent recorder.

Do not use third-party driver source without first resolving its licence; do
not disable macOS security mechanisms to install or test this driver.
