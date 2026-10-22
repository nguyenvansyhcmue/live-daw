#!/bin/zsh
set -euo pipefail

# Promote the validated control-law profile without changing any public knob,
# preset or state-serialization identifier.  This script intentionally does
# not alter the audio renderer, latency or live safety path.
SOURCE_ROOT="${VIBE_SOURCE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
BUILD_ROOT="${VIBE_BUILD:-$SOURCE_ROOT/build-studioforge-juce8-stable}"
PATCH_FILE="${0:A:h}/promote_hook2_calibrated_control_profile.patch"
FIXTURE_PATCH="${0:A:h}/fix_note_policy_dorian_fixture.patch"
MELODIC_FIXTURE_PATCH="${0:A:h}/fix_note_policy_melodic_minor_fixture.patch"
TRAJECTORY="$SOURCE_ROOT/VibeAutotune/CorrectionTrajectory.h"
NOTE_POLICY_TEST="$SOURCE_ROOT/tests/NotePolicyTest.cpp"

[[ -f "$TRAJECTORY" ]] || { print -u2 "Missing Vibe source: $TRAJECTORY"; exit 1; }
[[ -f "$PATCH_FILE" ]] || { print -u2 "Missing patch: $PATCH_FILE"; exit 1; }
[[ -f "$NOTE_POLICY_TEST" ]] || { print -u2 "Missing test fixture: $NOTE_POLICY_TEST"; exit 1; }

if rg -q 'productionFlexResidualScale = 0\.75' "$TRAJECTORY"; then
  print 'Already applied: hook-2 calibrated control profile'
else
  patch --dry-run -p1 -d "$SOURCE_ROOT" < "$PATCH_FILE"
  patch -p1 -d "$SOURCE_ROOT" < "$PATCH_FILE"
  print 'Applied: hook-2 calibrated control profile'
fi

# The previous fixture duplicated Melodic Minor where Dorian belongs. Correct
# the expected data so this regression tests the production scale map rather
# than a typo in its own oracle.
if rg -q '// Dorian' "$NOTE_POLICY_TEST"; then
  print 'Already applied: Dorian test-fixture correction'
else
  patch --dry-run -p1 -d "$SOURCE_ROOT" < "$FIXTURE_PATCH"
  patch -p1 -d "$SOURCE_ROOT" < "$FIXTURE_PATCH"
  print 'Applied: Dorian test-fixture correction'
fi

if rg -q '// Melodic Minor ascending' "$NOTE_POLICY_TEST"; then
  print 'Already applied: Melodic Minor test-fixture correction'
else
  patch --dry-run -p1 -d "$SOURCE_ROOT" < "$MELODIC_FIXTURE_PATCH"
  patch -p1 -d "$SOURCE_ROOT" < "$MELODIC_FIXTURE_PATCH"
  print 'Applied: Melodic Minor test-fixture correction'
fi

# Keep diagnostics as multiplicative deltas around the calibrated production
# curve: 1.00 means production; e.g. 1.10 is 10% more residual/hold.
[[ -d "$BUILD_ROOT" ]] || { print -u2 "Missing configured build: $BUILD_ROOT"; exit 1; }
cmake --build "$BUILD_ROOT" --target VibeAutotuneNotePolicyTest VibeAutotuneKeyScaleLivePathTest VibeAutotune_VST3 --parallel 8
"$BUILD_ROOT/VibeAutotuneNotePolicyTest"
"$BUILD_ROOT/VibeAutotuneKeyScaleLivePathTest"

BUILT_VST3="$BUILD_ROOT/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
INSTALLED_VST3="$HOME/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3"
BACKUP_TAG="$(date +%Y%m%d-%H%M%S)"
[[ -d "$BUILT_VST3" ]] || { print -u2 "VST3 build missing: $BUILT_VST3"; exit 1; }
if [[ -d "$INSTALLED_VST3" ]]; then
  mv "$INSTALLED_VST3" "${INSTALLED_VST3}.pre-hook2-calibration-$BACKUP_TAG"
fi
ditto --rsrc --extattr --acl "$BUILT_VST3" "$INSTALLED_VST3"
codesign --force --deep --sign - "$INSTALLED_VST3"

print ''
print 'Calibration profile is compiled, unit-checked, and installed as VST3.'
print 'Restart StudioForge, then run the Hook-2 regression and one holdout/live take before release.'
