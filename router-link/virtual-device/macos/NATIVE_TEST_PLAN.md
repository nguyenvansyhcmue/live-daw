# HAL native test preparation (not an installation approval)

Do not install until the owner accepts the risk and the signing/loading policy
for this particular machine and bundle has been verified. An ad-hoc seal only
proves integrity, not acceptance by coreaudiod. Do not change SIP, AMFI,
Gatekeeper, default audio devices, or unrelated HAL bundles.

## Preflight

From the repository root:

```sh
cmake --build build-live-release --target StudioForgeLinkHAL StudioForgeLinkHalNativeProbe
codesign --verify --strict --verbose=2 'build-live-release/router-link/StudioForgeLinkHAL.driver'
codesign -dvvv 'build-live-release/router-link/StudioForgeLinkHAL.driver'
ls -ld '/Library/Audio/Plug-Ins/HAL/StudioForgeLinkHAL.driver'
```

The default build signs ad-hoc after linking. It proves bundle integrity only;
it is not a release or loading guarantee. Once a valid Apple identity is in
the login keychain, create a separate release build directory and configure
the identity before the final build. The bundle must not be altered afterward:

```sh
security find-identity -v -p codesigning
cmake -S . -B build-link-release -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DSTUDIOFORGE_LINK_CODESIGN_IDENTITY='Developer ID Application: Your Name (TEAMID)'
cmake --build build-link-release --target StudioForgeLinkHAL StudioForgeLinkHalFoundationTests
codesign --verify --strict --verbose=2 \
  'build-link-release/router-link/StudioForgeLinkHAL.driver'
codesign -dvvv 'build-link-release/router-link/StudioForgeLinkHAL.driver'
```

This uses a secure timestamp for a non-ad-hoc identity and never uses
`--deep`. A Developer ID Installer identity is additionally required later if
the driver is delivered in a signed `.pkg`; it is not the identity used to
sign the `.driver` bundle itself.

## Controlled installation and recovery plan

An administrator must manually install the verified artifact into
`/Library/Audio/Plug-Ins/HAL/StudioForgeLinkHAL.driver`; no automation here
invokes sudo or reboots. First inspect any existing bundle at that exact path.
If it is an earlier StudioForge installation, move it to a unique backup
location **outside** `/Library/Audio/Plug-Ins/HAL` and record its ownership,
signature and original path. Never overwrite it or modify unrelated bundles.
Ensure the new destination is absent before copying the signed bundle, then
check root/wheel ownership, access permissions and strict signature integrity
on the installed copy. Explicitly reboot; do not silently restart coreaudiod.

For rollback, move only the newly installed `StudioForgeLinkHAL.driver` to a
new unique location outside the HAL directory; restore the recorded previous
bundle, if any, and reboot. If the system cannot boot normally, use macOS
Recovery and get administrator assistance; do not alter security settings.

## Discovery and real audio

Use Audio MIDI Setup and Core Audio enumeration to verify UID
`com.studioforge.link.virtual-duplex.v1`, stereo input/output and 44.1/48 kHz float.
The probe opens a device explicitly by UID, never changes defaults, and emits
audio. Run only when the selected routing is safe for speakers/listeners.
Start the reader first; in a second terminal run the writer while the reader
is active. Repeat with separate starts/stops and a writer restart:

```sh
build-live-release/router-link/StudioForgeLinkHalNativeProbe read com.studioforge.link.virtual-duplex.v1 20
build-live-release/router-link/StudioForgeLinkHalNativeProbe write com.studioforge.link.virtual-duplex.v1 10
```

An identifiable nonzero left/right pattern and sample continuity are reported.
Reported sample-time offset is modulo 2^20 frames and assumes the two Core
Audio client timestamps share the same device timeline. It is not a measured
FIFO occupancy or a general wall-clock round-trip latency. Investigate negative
offsets and timestamp validity; don't call offset a latency without confirming
the host's scheduling and clock semantics. Output format conversion can distort
the encoded pattern and lead to a false negative. Microphone permission may be
required, and command-line host permission behavior must be observed.

The current driver does not expose FIFO occupancy or exact underrun/overflow
counters to external clients. The probe reports silence/discontinuity, but
cannot infer exact queue depth, queue age after deliberate reader starvation,
or a precise driver underrun count. Stopping a reader is not equivalent to a
slow active reader. A safe real-host slow-reader test and usable telemetry are
still needed before claiming buffer-age/recovery verification. No callback is
intentionally blocked in this probe.

After any failure, inspect macOS Console and read-only logs, for example:

```sh
log show --last 10m --style compact --predicate 'process == "coreaudiod" OR process == "amfid"'
```

The log may require privileges or redact messages; no log entry means neither
success nor failure. Record the OS version, artifact signature, client errors,
audio results and any permission prompts. No OBS compatibility is implied.
