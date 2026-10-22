#!/bin/zsh
set -euo pipefail

ROOT="${STUDIOFORGE_ROOT:-/Users/hiimdrdey/code/daw}"
SCRIPT_DIR="${0:A:h}"
PATCH_FILE="$SCRIPT_DIR/studioforge-live-vibe-audibility-invariant.patch"
TRACE_PATCH_FILE="$SCRIPT_DIR/studioforge-live-trace-detail.patch"
TRACE_FORMAT_PATCH_FILE="$SCRIPT_DIR/studioforge-live-trace-format-fix.patch"
HOTPLUG_PATCH_FILE="$SCRIPT_DIR/studioforge-audio-hotplug-recovery.patch"
CONFIDENCE_GATE_PATCH_FILE="$SCRIPT_DIR/studioforge-live-confidence-hysteresis.patch"
DEVICE_SELECTION_PATCH_FILE="$SCRIPT_DIR/studioforge-audio-device-selection-fix.patch"
DIRECT_DRY_PATCH_FILE="$SCRIPT_DIR/studioforge-live-vibe-direct-dry-safety.patch"
ACTIVATION_TELEMETRY_PATCH_FILE="$SCRIPT_DIR/studioforge-live-tune-activation-telemetry.patch"
FX_CALLBACK_PATCH_FILE="$SCRIPT_DIR/studioforge-exact-plugin-block-contract.patch"
PLAYBACK_RECOVERY_PATCH_FILE="$SCRIPT_DIR/studioforge-playback-callback-recovery.patch"
TRACK_PDC_PATCH_FILE="$SCRIPT_DIR/studioforge-track-plugin-delay-compensation.patch"
VIBE_TRACE_SELECTION_PATCH_FILE="$SCRIPT_DIR/studioforge-trace-vibe-insert-selection.patch"
VIBE_TRANSITION_TRACE_PATCH_FILE="$SCRIPT_DIR/studioforge-vibe-transition-telemetry.patch"
VIBE_PROTECTION_TRACE_PATCH_FILE="$SCRIPT_DIR/studioforge-vibe-protection-reason-trace.patch"
AUTOMATED_VIBE_TRACE_PATCH_FILE="$SCRIPT_DIR/studioforge-automated-vibe-trace.patch"
AUTOMATED_VIBE_TRACE_RETRY_PATCH_FILE="$SCRIPT_DIR/studioforge-automated-vibe-trace-retry.patch"
VIBE_CONTINUITY_HOLD_PATCH_FILE="$SCRIPT_DIR/studioforge-live-continuity-hold.patch"
VIBE_CONTINUITY_HOLD_UI_PATCH_FILE="$SCRIPT_DIR/studioforge-live-continuity-hold-ui.patch"
BUILD="${STUDIOFORGE_RELEASE_BUILD_DIR:-$ROOT/build-live-release}"
DEST_APP="${STUDIOFORGE_DEST_APP:-/Users/hiimdrdey/Live daw/StudioForge Live DAW.app}"
SOURCE_APP="$BUILD/StudioForgeDAW_artefacts/Release/StudioForge DAW.app"

[[ -f "$PATCH_FILE" ]] || { print -u2 "Missing patch: $PATCH_FILE"; exit 1; }
[[ -f "$TRACE_PATCH_FILE" ]] || { print -u2 "Missing trace patch: $TRACE_PATCH_FILE"; exit 1; }
[[ -f "$TRACE_FORMAT_PATCH_FILE" ]] || { print -u2 "Missing trace format patch: $TRACE_FORMAT_PATCH_FILE"; exit 1; }
[[ -f "$HOTPLUG_PATCH_FILE" ]] || { print -u2 "Missing hot-plug recovery patch: $HOTPLUG_PATCH_FILE"; exit 1; }
[[ -f "$CONFIDENCE_GATE_PATCH_FILE" ]] || { print -u2 "Missing confidence-gate patch: $CONFIDENCE_GATE_PATCH_FILE"; exit 1; }
[[ -f "$DEVICE_SELECTION_PATCH_FILE" ]] || { print -u2 "Missing device-selection patch: $DEVICE_SELECTION_PATCH_FILE"; exit 1; }
[[ -f "$DIRECT_DRY_PATCH_FILE" ]] || { print -u2 "Missing direct-mic safety patch: $DIRECT_DRY_PATCH_FILE"; exit 1; }
[[ -f "$ACTIVATION_TELEMETRY_PATCH_FILE" ]] || { print -u2 "Missing activation-telemetry patch: $ACTIVATION_TELEMETRY_PATCH_FILE"; exit 1; }
[[ -f "$FX_CALLBACK_PATCH_FILE" ]] || { print -u2 "Missing FX callback contract patch: $FX_CALLBACK_PATCH_FILE"; exit 1; }
[[ -f "$PLAYBACK_RECOVERY_PATCH_FILE" ]] || { print -u2 "Missing playback recovery patch: $PLAYBACK_RECOVERY_PATCH_FILE"; exit 1; }
[[ -f "$TRACK_PDC_PATCH_FILE" ]] || { print -u2 "Missing track PDC patch: $TRACK_PDC_PATCH_FILE"; exit 1; }
[[ -f "$VIBE_TRACE_SELECTION_PATCH_FILE" ]] || { print -u2 "Missing Vibe trace selection patch: $VIBE_TRACE_SELECTION_PATCH_FILE"; exit 1; }
[[ -f "$VIBE_TRANSITION_TRACE_PATCH_FILE" ]] || { print -u2 "Missing Vibe transition trace patch: $VIBE_TRANSITION_TRACE_PATCH_FILE"; exit 1; }
[[ -f "$VIBE_PROTECTION_TRACE_PATCH_FILE" ]] || { print -u2 "Missing Vibe protection trace patch: $VIBE_PROTECTION_TRACE_PATCH_FILE"; exit 1; }
[[ -f "$AUTOMATED_VIBE_TRACE_PATCH_FILE" ]] || { print -u2 "Missing automated Vibe trace patch: $AUTOMATED_VIBE_TRACE_PATCH_FILE"; exit 1; }
[[ -f "$AUTOMATED_VIBE_TRACE_RETRY_PATCH_FILE" ]] || { print -u2 "Missing automated Vibe trace retry patch: $AUTOMATED_VIBE_TRACE_RETRY_PATCH_FILE"; exit 1; }
[[ -f "$VIBE_CONTINUITY_HOLD_PATCH_FILE" ]] || { print -u2 "Missing Vibe continuity-hold patch: $VIBE_CONTINUITY_HOLD_PATCH_FILE"; exit 1; }
[[ -f "$VIBE_CONTINUITY_HOLD_UI_PATCH_FILE" ]] || { print -u2 "Missing Vibe continuity-hold UI patch: $VIBE_CONTINUITY_HOLD_UI_PATCH_FILE"; exit 1; }
[[ -f "$BUILD/CMakeCache.txt" ]] || { print -u2 "Missing configured build: $BUILD"; exit 1; }

cd "$ROOT"
if git apply --check --recount "$PATCH_FILE" 2>/dev/null; then
  git apply --recount "$PATCH_FILE"
  print "Applied live audibility invariant."
elif git apply --reverse --check --recount "$PATCH_FILE" 2>/dev/null \
  || { grep -q 'Final live-audibility invariant' "$ROOT/Source/Plugins/NativeVibeAutotuneProcessor.cpp" \
       && grep -q 'hardDryRescue' "$ROOT/Source/Plugins/NativeVibeAutotuneProcessor.cpp"; }; then
  print "Live audibility invariant is already applied."
else
  print -u2 "Audibility patch does not match the current source tree."
  exit 1
fi

# Numeric detector/target/correction telemetry makes a live trace capable of
# separating a late target decision from a late renderer handoff. It contains
# no UI strings or heap work in the audio callback.
if git apply --check --recount "$VIBE_TRANSITION_TRACE_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$VIBE_TRANSITION_TRACE_PATCH_FILE"
  print "Applied Vibe transition telemetry."
elif git apply --reverse --check --recount "$VIBE_TRANSITION_TRACE_PATCH_FILE" 2>/dev/null \
  || { grep -q 'vibeCorrectionCents' "$ROOT/Source/AudioEngine/AudioDiagnosticTracer.h" \
       && grep -q 'publishedTrackerTargetMidiNote' "$ROOT/Source/Plugins/NativeVibeAutotuneProcessor.h"; }; then
  print "Vibe transition telemetry is already applied."
else
  print -u2 "Vibe transition telemetry patch does not match the current source tree."
  exit 1
fi

# A protection counter alone cannot distinguish a legitimate renderer safety
# intervention from an overload. Export the objective fault reason before
# changing any live safety threshold.
if git apply --check --recount "$VIBE_PROTECTION_TRACE_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$VIBE_PROTECTION_TRACE_PATCH_FILE"
  print "Applied Vibe protection-reason telemetry."
elif git apply --reverse --check --recount "$VIBE_PROTECTION_TRACE_PATCH_FILE" 2>/dev/null \
  || { grep -q 'vibeRendererCollapsed' "$ROOT/Source/AudioEngine/AudioDiagnosticTracer.h" \
       && grep -q 'publishedRendererCollapsed' "$ROOT/Source/Plugins/NativeVibeAutotuneProcessor.h"; }; then
  print "Vibe protection-reason telemetry is already applied."
else
  print -u2 "Vibe protection-reason telemetry patch does not match the current source tree."
  exit 1
fi

# Tracker uncertainty is not a renderer failure. Preserve the existing Vibe
# DSP and its parameters, but keep the verified wet path through a bounded
# post-dropout continuity tail before its normal release starts.
if git apply --check --recount "$VIBE_CONTINUITY_HOLD_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$VIBE_CONTINUITY_HOLD_PATCH_FILE"
  print "Applied Vibe continuity Hold contract."
elif git apply --reverse --check --recount "$VIBE_CONTINUITY_HOLD_PATCH_FILE" 2>/dev/null +  || grep -q 'continuityTailSamples' "$ROOT/Source/Plugins/NativeVibeAutotuneProcessor.h"; then
  print "Vibe continuity Hold contract is already applied."
else
  print -u2 "Vibe continuity Hold patch does not match the current source tree."
  exit 1
fi

if git apply --check --recount "$VIBE_CONTINUITY_HOLD_UI_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$VIBE_CONTINUITY_HOLD_UI_PATCH_FILE"
  print "Applied Vibe Hold state UI."
elif git apply --reverse --check --recount "$VIBE_CONTINUITY_HOLD_UI_PATCH_FILE" 2>/dev/null +  || grep -q 'LiveProcessorState::holding' "$ROOT/Source/UI/InspectorComponents.cpp"; then
  print "Vibe Hold state UI is already applied."
else
  print -u2 "Vibe Hold UI patch does not match the current source tree."
  exit 1
fi

# A first-class launch flag prepares a disposable live vocal route, inserts
# native Vibe through the existing integration service, and starts tracing.
# This avoids brittle screen-coordinate automation in support sessions.
if git apply --check --recount "$AUTOMATED_VIBE_TRACE_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$AUTOMATED_VIBE_TRACE_PATCH_FILE"
  print "Applied automated Vibe trace launch path."
elif git apply --reverse --check --recount "$AUTOMATED_VIBE_TRACE_PATCH_FILE" 2>/dev/null \
  || { grep -q 'startAutomatedVibeTrace' "$ROOT/Source/UI/MainComponent.h" \
       && grep -q 'automated-vibe-trace' "$ROOT/Source/Core/Main.cpp"; }; then
  print "Automated Vibe trace launch path is already applied."
else
  print -u2 "Automated Vibe trace launch patch does not match the current source tree."
  exit 1
fi

# USB interfaces can become available after the first launch callback. Retry
# for a bounded 10-second window; the component has an idempotence latch so
# a ready device creates exactly one disposable trace session.
if git apply --check --recount "$AUTOMATED_VIBE_TRACE_RETRY_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$AUTOMATED_VIBE_TRACE_RETRY_PATCH_FILE"
  print "Applied automated Vibe trace device-readiness retry."
elif git apply --reverse --check --recount "$AUTOMATED_VIBE_TRACE_RETRY_PATCH_FILE" 2>/dev/null +  || grep -q 'automatedVibeTraceStarted' "$ROOT/Source/UI/MainComponent.h"; then
  print "Automated Vibe trace device-readiness retry is already applied."
else
  print -u2 "Automated Vibe trace retry patch does not match the current source tree."
  exit 1
fi

if git apply --check --recount "$TRACE_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$TRACE_PATCH_FILE"
  print "Applied detailed live trace telemetry."
elif git apply --reverse --check --recount "$TRACE_PATCH_FILE" 2>/dev/null \
  || { grep -q 'trackPostFxPeak' "$ROOT/Source/AudioEngine/AudioDiagnosticTracer.h" \
       && grep -q 'vibeProtectionCount' "$ROOT/Source/AudioEngine/AudioDiagnosticTracer.cpp"; }; then
  print "Detailed live trace telemetry is already applied."
else
  print -u2 "Trace patch does not match the current source tree."
  exit 1
fi

# The old trace only inspected an input-monitored track. Select the Vibe
# insert first so playback/raw-file tests expose its actual tracker and wet
# state instead of showing a misleading all-zero telemetry row.
if git apply --check --recount "$VIBE_TRACE_SELECTION_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$VIBE_TRACE_SELECTION_PATCH_FILE"
  print "Applied Vibe-insert trace selection."
elif git apply --reverse --check --recount "$VIBE_TRACE_SELECTION_PATCH_FILE" 2>/dev/null \
  || grep -q 'rendered/raw clip is diagnosable' "$ROOT/Source/AudioEngine/AudioEngine.cpp"; then
  print "Vibe-insert trace selection is already applied."
else
  print -u2 "Vibe trace selection patch does not match the current source tree."
  exit 1
fi

if git apply --check --recount "$TRACE_FORMAT_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$TRACE_FORMAT_PATCH_FILE"
  print "Applied trace CSV format fix."
elif git apply --reverse --check --recount "$TRACE_FORMAT_PATCH_FILE" 2>/dev/null \
  || grep -q 'String(e.trackId) + ","$' "$ROOT/Source/AudioEngine/AudioDiagnosticTracer.cpp"; then
  print "Trace CSV format fix is already applied."
else
  print -u2 "Trace format patch does not match the current source tree."
  exit 1
fi

if git apply --check --recount "$HOTPLUG_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$HOTPLUG_PATCH_FILE"
  print "Applied soundcard hot-plug recovery."
elif git apply --reverse --check --recount "$HOTPLUG_PATCH_FILE" 2>/dev/null \
  || grep -q 'recoverPreferredAudioDeviceAfterHotPlug' "$ROOT/Source/AudioEngine/AudioEngine.cpp"; then
  print "Soundcard hot-plug recovery is already applied."
else
  print -u2 "Soundcard hot-plug patch does not match the current source tree."
  exit 1
fi

if git apply --check --recount "$CONFIDENCE_GATE_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$CONFIDENCE_GATE_PATCH_FILE"
  print "Applied live confidence hysteresis gate."
elif git apply --reverse --check --recount "$CONFIDENCE_GATE_PATCH_FILE" 2>/dev/null \
  || { grep -q 'LiveTuneConfidenceGate' "$ROOT/Source/Plugins/NativeVibeAutotuneProcessor.h" \
       && grep -q 'dropoutHoldSeconds' "$ROOT/Source/Plugins/LiveTuneConfidenceGate.h"; }; then
  print "Live confidence hysteresis gate is already applied."
else
  print -u2 "Confidence-gate patch does not match the current source tree."
  exit 1
fi

if git apply --check --recount "$DIRECT_DRY_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$DIRECT_DRY_PATCH_FILE"
  print "Applied direct-mic safety path for unverified Vibe renderer."
elif git apply --reverse --check --recount "$DIRECT_DRY_PATCH_FILE" 2>/dev/null \
  || { grep -q 'rendererIsAudible' "$ROOT/Source/Plugins/NativeVibeAutotuneProcessor.cpp" \
       && grep -q 'verifyUnverifiedRendererKeepsDirectMic' "$ROOT/Tests/NativeVibeAutotuneSmokeTest.cpp"; }; then
  print "Direct-mic safety path is already applied."
else
  print -u2 "Direct-mic safety patch does not match the current source tree."
  exit 1
fi

if git apply --check --recount "$ACTIVATION_TELEMETRY_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$ACTIVATION_TELEMETRY_PATCH_FILE"
  print "Applied tracker-to-wet activation telemetry."
elif git apply --reverse --check --recount "$ACTIVATION_TELEMETRY_PATCH_FILE" 2>/dev/null \
  || { grep -q 'vibeTrackerConfidence' "$ROOT/Source/AudioEngine/AudioDiagnosticTracer.h" \
       && grep -q 'publishedTrackerConfidence' "$ROOT/Source/Plugins/NativeVibeAutotuneProcessor.h"; }; then
  print "Tracker-to-wet activation telemetry is already applied."
else
  print -u2 "Activation-telemetry patch does not match the current source tree."
  exit 1
fi

if git apply --check --recount "$DEVICE_SELECTION_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$DEVICE_SELECTION_PATCH_FILE"
  print "Applied explicit audio-device selection fix."
elif git apply --reverse --check --recount "$DEVICE_SELECTION_PATCH_FILE" 2>/dev/null \
  || { grep -q 'preferredDeviceWasUnavailable' "$ROOT/Source/AudioEngine/AudioEngine.h" \
       && grep -q 'explicit Device Settings selection' "$ROOT/Source/AudioEngine/AudioEngine.cpp"; }; then
  print "Explicit audio-device selection fix is already applied."
else
  print -u2 "Device-selection patch does not match the current source tree."
  exit 1
fi

if git apply --check --recount "$PLAYBACK_RECOVERY_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$PLAYBACK_RECOVERY_PATCH_FILE"
  print "Applied stalled-CoreAudio recovery on Play."
elif git apply --reverse --check --recount "$PLAYBACK_RECOVERY_PATCH_FILE" 2>/dev/null \
  || grep -q 'restartAudioDeviceIfCallbackStalled' "$ROOT/Source/AudioEngine/AudioEngine.cpp"; then
  print "Stalled-CoreAudio recovery is already applied."
else
  print -u2 "Playback recovery patch does not match the current source tree."
  exit 1
fi

# This is deliberately installed after the live-only patches because it fixes
# the general DAW insert contract: every audio effect must receive precisely
# the CoreAudio callback length, never the preallocated backing-buffer size.
if git apply --check --recount "$FX_CALLBACK_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$FX_CALLBACK_PATCH_FILE"
  print "Applied exact callback-span contract for all FX inserts."
elif git apply --reverse --check --recount "$FX_CALLBACK_PATCH_FILE" 2>/dev/null \
  || grep -q 'an insert receives the exact device callback span' "$ROOT/Tests/CorePlaybackMixerTests.cpp"; then
  print "Exact callback-span contract is already applied."
else
  print -u2 "FX callback contract patch does not match the current source tree."
  exit 1
fi

# Studio mode needs compensation as well as the low-latency Stage path. The
# mixer delays shorter insert chains by the reported latency difference before
# summing, so Vibe stays aligned with backing tracks without changing Vibe DSP.
if git apply --check --recount "$TRACK_PDC_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$TRACK_PDC_PATCH_FILE"
  print "Applied track plugin delay compensation (Studio PDC)."
elif git apply --reverse --check --recount "$TRACK_PDC_PATCH_FILE" 2>/dev/null \
  || grep -q 'track plugin latency compensation aligns a delayed insert' "$ROOT/Tests/CorePlaybackMixerTests.cpp"; then
  print "Track plugin delay compensation is already applied."
else
  print -u2 "Track PDC patch does not match the current source tree."
  exit 1
fi


print "Building DAW and host-contract tests..."
cmake --build "$BUILD" --target StudioForgeDAW StudioForgeCoreTests StudioForgeNativeVibeSmokeTest StudioForgeLiveTuneConfidenceGateTest --parallel 8
print "Running host-contract and live safety tests..."
"$BUILD/StudioForgeCoreTests"
"$BUILD/StudioForgeNativeVibeSmokeTest"
"$BUILD/StudioForgeLiveTuneConfidenceGateTest"

[[ -d "$SOURCE_APP" ]] || { print -u2 "Built app missing: $SOURCE_APP"; exit 1; }
osascript -e 'tell application id "com.StudioForge.StudioForgeDAW" to quit' 2>/dev/null || true
sleep 2
mkdir -p "${DEST_APP:h}"
if [[ -e "$DEST_APP" ]]; then
  BACKUP_APP="${DEST_APP:r} backup audibility-$(date +%Y%m%d-%H%M%S).app"
  mv "$DEST_APP" "$BACKUP_APP"
  print "Previous app moved to: $BACKUP_APP"
fi
ditto --rsrc --extattr --acl "$SOURCE_APP" "$DEST_APP"
codesign --force --deep --sign - "$DEST_APP"
xattr -dr com.apple.quarantine "$DEST_APP" 2>/dev/null || true
codesign --verify --deep --strict "$DEST_APP"
print "LIVE AUDIBILITY HOTFIX INSTALLED: $DEST_APP"
print "Opening automated Vibe trace: Vocal 1 + native Vibe + LIVE monitoring + trace."
"$DEST_APP/Contents/MacOS/StudioForge DAW" --automated-vibe-trace >/private/tmp/studioforge-automated-vibe-trace.log 2>&1 &
