#!/bin/zsh
set -euo pipefail

ROOT="${STUDIOFORGE_ROOT:-/Users/hiimdrdey/code/daw}"
SCRIPT_DIR="${0:A:h}"
HOST_PATCH_FILE="$SCRIPT_DIR/studioforge-unified-plugin-host-phase1-v2.patch"
EDITOR_PATCH_FILE="$SCRIPT_DIR/studioforge-plugin-editor-lifecycle-phase2.patch"
MIXER_PDC_PATCH_FILE="$SCRIPT_DIR/studioforge-mixer-rack-and-pdc-phase3.patch"
MIXER_EDITOR_PATCH_FILE="$SCRIPT_DIR/studioforge-unified-mixer-editor-session-phase4.patch"
PDC_AUX_FIXTURE_PATCH_FILE="$SCRIPT_DIR/studioforge-pdc-aux-output-fixture-phase5.patch"
MONITORING_POLICY_PATCH_FILE="$SCRIPT_DIR/studioforge-monitoring-latency-policy-phase6.patch"
BUILD="${STUDIOFORGE_RELEASE_BUILD_DIR:-$ROOT/build-live-release}"
PACKAGE_DIR="${STUDIOFORGE_PACKAGE_DIR:-/Users/hiimdrdey/Live daw}"
SOURCE_APP="$BUILD/StudioForgeDAW_artefacts/Release/StudioForge DAW.app"
DEST_APP="$PACKAGE_DIR/StudioForge Live DAW.app"
STAMP=$(date +%Y%m%d-%H%M%S)

[[ -f "$ROOT/CMakeLists.txt" ]] || { print -u2 "Missing StudioForge source: $ROOT"; exit 1; }
[[ -f "$HOST_PATCH_FILE" ]] || { print -u2 "Missing host-contract patch: $HOST_PATCH_FILE"; exit 1; }
[[ -f "$EDITOR_PATCH_FILE" ]] || { print -u2 "Missing editor-lifecycle patch: $EDITOR_PATCH_FILE"; exit 1; }
[[ -f "$MIXER_PDC_PATCH_FILE" ]] || { print -u2 "Missing mixer/PDC patch: $MIXER_PDC_PATCH_FILE"; exit 1; }
[[ -f "$MIXER_EDITOR_PATCH_FILE" ]] || { print -u2 "Missing Mixer editor-session patch: $MIXER_EDITOR_PATCH_FILE"; exit 1; }
[[ -f "$PDC_AUX_FIXTURE_PATCH_FILE" ]] || { print -u2 "Missing AUX PDC fixture patch: $PDC_AUX_FIXTURE_PATCH_FILE"; exit 1; }
[[ -f "$MONITORING_POLICY_PATCH_FILE" ]] || { print -u2 "Missing monitoring-policy patch: $MONITORING_POLICY_PATCH_FILE"; exit 1; }
[[ -x "$SCRIPT_DIR/deploy_latest_vibeautotune_to_daw.zsh" ]] \
  || { print -u2 "Missing Vibe deployment script"; exit 1; }

cd "$ROOT"

if git apply --check --recount "$HOST_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$HOST_PATCH_FILE"
  print "Applied: ${HOST_PATCH_FILE:t}"
elif git apply --reverse --check --recount "$HOST_PATCH_FILE" 2>/dev/null; then
  print "Already applied: ${HOST_PATCH_FILE:t}"
elif grep -q 'juce::File bundledVst3Directory()' Source/Plugins/PluginHostService.cpp \
  && ! grep -q 'NativeVibeAutotuneProcessor.h' Source/Plugins/PluginHostService.cpp \
  && grep -q 'build-studioforge-host/VibeAutotune_artefacts' CMakeLists.txt \
  && grep -q 'existing->getPersistentIdentifier() != vibe->createIdentifierString()' \
      Source/Control/PitchCorrectionIntegrationService.cpp; then
  print "Already applied (verified by implementation markers): ${HOST_PATCH_FILE:t}"
else
  print -u2 "Host-contract patch does not match the current source tree: $HOST_PATCH_FILE"
  exit 1
fi

# This patch is intentionally in portable unified-diff form. `patch` accepts
# the vendor/source state even when it already contains unrelated local DAW
# work, whereas git-apply requires a pristine index context.
if grep -q 'fxRacksExpanded' Source/UI/MixerPane.h \
  && grep -q 'Zero is a true bypass' Source/AudioEngine/AudioEngine.cpp \
  && grep -q 'stageDirectPathForBusCompensation' Source/AudioEngine/AudioEngine.cpp; then
  print "Already applied (verified by implementation markers): ${MIXER_PDC_PATCH_FILE:t}"
elif patch -p1 --dry-run --batch < "$MIXER_PDC_PATCH_FILE" >/dev/null 2>&1; then
  patch -p1 --batch < "$MIXER_PDC_PATCH_FILE"
  print "Applied: ${MIXER_PDC_PATCH_FILE:t}"
else
  print -u2 "Mixer/PDC patch does not match the current source tree: $MIXER_PDC_PATCH_FILE"
  exit 1
fi

# Phase 4 is based on the compact Mixer rack layout from Phase 3, so apply it
# only after that layout is in place.
if grep -q 'openPluginEditorNow' Source/UI/MixerPane.h \
  && grep -q 'MixerPluginEditorHost' Source/UI/MixerPane.cpp \
  && grep -q 'pluginEditorWindows' Source/UI/MixerPane.h; then
  print "Already applied (verified by implementation markers): ${MIXER_EDITOR_PATCH_FILE:t}"
elif patch -p1 --dry-run --batch < "$MIXER_EDITOR_PATCH_FILE" >/dev/null 2>&1; then
  patch -p1 --batch < "$MIXER_EDITOR_PATCH_FILE"
  print "Applied: ${MIXER_EDITOR_PATCH_FILE:t}"
else
  print -u2 "Mixer editor-session patch does not match the current source tree: $MIXER_EDITOR_PATCH_FILE"
  exit 1
fi

# A track routed *to* an AUX is just as active as a send to that AUX. Without
# this edge in the latency calculation, Studio playback can mix its return
# late against a direct track. The accompanying impulse fixture proves the
# two routes land on the exact same sample before this is accepted in a build.
if grep -q 'testAuxOutputLatencyCompensation' tests/CorePlaybackMixerTests.cpp \
  && grep -q 'outputBusIndex = structure.getBusIndex' Source/AudioEngine/AudioEngine.cpp; then
  print "Already applied (verified by implementation markers): ${PDC_AUX_FIXTURE_PATCH_FILE:t}"
elif patch -p1 --dry-run --batch < "$PDC_AUX_FIXTURE_PATCH_FILE" >/dev/null 2>&1; then
  patch -p1 --batch < "$PDC_AUX_FIXTURE_PATCH_FILE"
  print "Applied: ${PDC_AUX_FIXTURE_PATCH_FILE:t}"
else
  print -u2 "AUX PDC fixture patch does not match the current source tree: $PDC_AUX_FIXTURE_PATCH_FILE"
  exit 1
fi

# Audio Settings exposes only policy which has a realtime-safe engine contract:
# global software-monitor safety gate, focused-track monitor mode, Live
# low-latency protection and Studio PDC. The controls persist with the device
# setup; callbacks read atomics only.
if grep -q 'setSoftwareMonitoringEnabled' Source/AudioEngine/AudioEngine.h \
  && grep -q 'settingsTabs.addTab("Monitoring"' Source/UI/DeviceSettingsPanel.cpp \
  && grep -q 'testMonitoringPolicyGates' tests/CorePlaybackMixerTests.cpp; then
  print "Already applied (verified by implementation markers): ${MONITORING_POLICY_PATCH_FILE:t}"
elif patch -p1 --dry-run --batch < "$MONITORING_POLICY_PATCH_FILE" >/dev/null 2>&1; then
  patch -p1 --batch < "$MONITORING_POLICY_PATCH_FILE"
  print "Applied: ${MONITORING_POLICY_PATCH_FILE:t}"
else
  print -u2 "Monitoring-policy patch does not match the current source tree: $MONITORING_POLICY_PATCH_FILE"
  exit 1
fi

if git apply --check --recount "$EDITOR_PATCH_FILE" 2>/dev/null; then
  git apply --recount "$EDITOR_PATCH_FILE"
  print "Applied: ${EDITOR_PATCH_FILE:t}"
elif git apply --reverse --check --recount "$EDITOR_PATCH_FILE" 2>/dev/null; then
  print "Already applied: ${EDITOR_PATCH_FILE:t}"
elif grep -q 'getInstanceWithoutCreating' Source/Plugins/PluginHostService.cpp \
  && ! grep -q 'isVibeAutotune' Source/UI/InspectorComponents.cpp \
  && grep -q 'void childBoundsChanged (juce::Component\* child) override' Source/UI/InspectorComponents.cpp; then
  print "Already applied (verified by implementation markers): ${EDITOR_PATCH_FILE:t}"
else
  print -u2 "Editor-lifecycle patch does not match the current source tree: $EDITOR_PATCH_FILE"
  exit 1
fi

# Architectural guard: Auto Key remains an explicit product integration, but
# the generic plug-in host may not switch DSP implementations by product name.
grep -q 'findVibeAutotune()' Source/Control/PitchCorrectionIntegrationService.cpp \
  || { print -u2 "Auto Key -> Vibe discovery is missing"; exit 1; }
grep -q 'VibeAutotuneAdapter {}.resolve' Source/Control/PitchCorrectionIntegrationService.cpp \
  || { print -u2 "Auto Key -> Vibe root/scale mapping is missing"; exit 1; }
if grep -q 'NativeVibeAutotuneProcessor' Source/Plugins/PluginHostService.cpp; then
  print -u2 "Generic PluginHostService still contains a Vibe-only DSP path"
  exit 1
fi
if grep -q 'STUDIOFORGE_NATIVE_VIBE_AVAILABLE=1' CMakeLists.txt; then
  print -u2 "StudioForgeDAW still enables the private native Vibe path"
  exit 1
fi
print "Contract check passed: Auto Key controls Vibe; audio hosting remains format-generic."
print "Editor contract passed: editor creation stays on the UI thread and retains processor ownership."
print "Mixer editor contract passed: track and Master editors use the same deferred, owner-retained session semantics as Inspector."
print "Mixer/PDC contract passed: eight fixed realtime-safe inserts are compact by default; Studio and Live use distinct PDC policies."
print "PDC fixture contract passed: direct and AUX-output paths are sample-aligned in Studio mode."
print "Monitoring policy passed: Audio Settings owns persistent global monitor/PDC choices; the callback reads lock-free state."

print "Building and installing the latest canonical VibeAutotune AU/VST3..."
STUDIOFORGE_ROOT="$ROOT" STUDIOFORGE_SKIP_OPEN=1 \
  zsh "$SCRIPT_DIR/deploy_latest_vibeautotune_to_daw.zsh"

if [[ ! -f "$BUILD/CMakeCache.txt" ]]; then
  JUCE_SOURCE="$ROOT/build-macos-arm64/_deps/juce-src"
  [[ -d "$JUCE_SOURCE" ]] || { print -u2 "Pinned JUCE checkout is missing: $JUCE_SOURCE"; exit 1; }
  cmake -S "$ROOT" -B "$BUILD" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DBUILD_TESTING=ON \
    -DFETCHCONTENT_SOURCE_DIR_JUCE="$JUCE_SOURCE"
fi

print "Building the unified StudioForge host..."
cmake --build "$BUILD" --target StudioForgeDAW StudioForgeCoreTests --parallel 8

print "Running deterministic core/host regression tests..."
"$BUILD/StudioForgeCoreTests"

[[ -d "$SOURCE_APP" ]] || { print -u2 "Release app was not produced: $SOURCE_APP"; exit 1; }
[[ -d "$SOURCE_APP/Contents/Resources/PlugIns/VST3/VibeAutotune.vst3" ]] \
  || { print -u2 "Latest VibeAutotune was not embedded in the DAW bundle"; exit 1; }

osascript -e 'tell application id "com.StudioForge.StudioForgeDAW" to quit' 2>/dev/null || true
mkdir -p "$PACKAGE_DIR"
if [[ -e "$DEST_APP" ]]; then
  BACKUP_APP="$PACKAGE_DIR/StudioForge Live DAW backup $STAMP.app"
  mv "$DEST_APP" "$BACKUP_APP"
  print "Previous package moved to: $BACKUP_APP"
fi

ditto --rsrc --extattr --acl "$SOURCE_APP" "$DEST_APP"
codesign --force --deep --sign - "$DEST_APP"
xattr -dr com.apple.quarantine "$DEST_APP" 2>/dev/null || true
codesign --verify --deep --strict "$DEST_APP"

print ""
print "DEPLOYED: $DEST_APP"
print "AUTO KEY: detects the song and writes Root Key + Scale directly to VibeAutotune."
print "HOST: VibeAutotune now uses the same JUCE VST3 hosting path as other plug-ins."

if [[ "${STUDIOFORGE_SKIP_OPEN:-0}" != "1" ]]; then
  open "$DEST_APP"
fi
