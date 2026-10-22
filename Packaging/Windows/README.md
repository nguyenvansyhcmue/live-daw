# StudioForge Link on Windows

The Windows release is intentionally blocked until a real Windows audio-driver
artifact exists. The current repository has WASAPI/ASIO **host** support in the
DAW and WASAPI loopback capture in Tune-AI; neither one creates a system-visible
virtual playback/recording device.

An ASIO-Link-class product needs two different boundaries:

1. a virtual WDM/AVStream audio endpoint so browsers, players and normal Windows
   applications can select StudioForge Link;
2. an ASIO driver/router for low-latency ASIO clients, sharing audio through a
   versioned, bounded transport service without blocking an audio callback.

Before a public x64 package is allowed, the Windows runner must provide:

- Visual Studio 2022, CMake, Ninja, Python x64 and the Windows SDK/WDK;
- the legally obtained ASIO SDK configured through `STUDIOFORGE_ASIO_SDK_DIR`;
- an EV code-signing certificate and Windows Hardware Developer account;
- a Microsoft-signed driver package produced through Partner Center/HLK;
- clean-machine tests for install, upgrade, rollback, sleep/wake, device loss,
  44.1/48 kHz negotiation and simultaneous playback/recording clients.

Do not package the macOS HAL binary, register an arbitrary DLL under the ASIO
registry key, disable Secure Boot, or ask users to enable test-signing mode.
