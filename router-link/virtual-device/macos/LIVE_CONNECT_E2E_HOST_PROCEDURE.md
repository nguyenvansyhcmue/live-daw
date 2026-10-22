# StudioForge LIVE CONNECT — host-side E2E procedure

Run this procedure in a normal macOS Terminal after BlackHole has appeared in
Audio MIDI Setup. It is intentionally read-only: it does not change the macOS
default input/output device, install software, restart Core Audio, or modify a
driver bundle.

The Codex execution sandbox cannot enumerate the host's Core Audio devices, so
the outputs below are the evidence for this milestone.

## 1. Build the DAW and probes

```sh
cd /Users/hiimdrdey/code/daw
cmake --build build-live-release --target StudioForgeDAW StudioForgeCoreAudioEnvironmentProbe StudioForgeLinkHalNativeProbe -j 4
```

## 2. Enumerate the actual host endpoint

```sh
build-live-release/router-link/StudioForgeCoreAudioEnvironmentProbe | tee /tmp/studioforge-coreaudio-environment.txt
```

For the BlackHole candidate, retain these lines in the report:

- `name`, stable `uid`, `alive`, and `transport=virtual`
- input and output channel counts (both must be 2)
- current nominal rate and available nominal-rate ranges
- input/output PCM format (expected 44.1 or 48 kHz Float32)

Do not use a physical speaker endpoint. BlackHole must be visible as an OS
virtual device; this does not prove it is carrying audio yet.

Set the exact UID printed by the probe (not the device name):

```sh
export SF_LIVE_UID='paste-the-BlackHole-UID-here'
```

## 3. Verify the virtual device independently of StudioForge

This is a two-process Core Audio test. The writer emits a known interleaved
stereo pattern (`right = -left`); the reader captures the input side.

```sh
PROBE=build-live-release/router-link/StudioForgeLinkHalNativeProbe
"$PROBE" read "$SF_LIVE_UID" 12 | tee /tmp/studioforge-loopback-read.txt &
READER_PID=$!
sleep 1
"$PROBE" write "$SF_LIVE_UID" 10 | tee /tmp/studioforge-loopback-write.txt
wait "$READER_PID"
```

Required reader evidence:

- `callbacks > 0`
- `nonzero > 0` and `pattern_matched > 0`
- `stereo_identity_failures=0`
- `discontinuities=0` for the short test
- measured `sample_time_offset_frames_min/max`, when timestamps are supplied

The offset is a device-timeline observation. It is not a complete latency
measurement for StudioForge, and FIFO occupancy is not exposed by BlackHole.

If this step fails, stop. The issue is virtual-device setup, format, or Core
Audio permissions—not StudioForge LIVE CONNECT.

## 4. Verify StudioForge routing to an independent recorder

1. Launch the built StudioForge app.
2. Keep StudioForge's primary monitor device set to the physical speakers or
   soundcard. Do not choose BlackHole as the main device or macOS default.
3. Open **Audio Device Settings** and select **BlackHole 2ch (Virtual)** in
   `STREAM OUTPUT`. Confirm the primary device uses the same 44.1/48 kHz rate.
4. Click `LIVE CONNECT`. The button may reach `LIVE READY` before its output
   callback begins; it reaches `LIVE ACTIVE` only after callback progress.
5. Create/play a known stereo source through StudioForge post-master output.
   For a simple identity check, pan a short spoken/impulse source left, then a
   different source right. Keep the session playing for at least 60 seconds.
6. In OBS (or a separate recording application), add **BlackHole 2ch** as an
   audio input. Record a file; do not rely solely on its meter.
7. Inspect the recording: left/right identity, continuity, no unexpected
   double monitoring, and an approximate onset delay from a visible/sounded
   impulse. Record any dropout/drift during the 60-second run.
8. Click `LIVE ACTIVE` to disconnect. Confirm OBS receives silence while the
   physical StudioForge monitor remains unchanged.

## Result classification

- **Virtual loopback PASS**: step 3 emits matching non-silent PCM.
- **StudioForge E2E PASS**: step 4 produces an independently recorded
  StudioForge post-master signal with correct L/R and continuity.
- **PARTIAL/BLOCKED**: include the exact failed step, probe output, DAW LIVE
  state, selected UID, sample rates, recorder result, and whether the physical
  monitor remained intact.

Neither `LIVE ACTIVE` nor an OBS meter alone is proof of E2E capture.
