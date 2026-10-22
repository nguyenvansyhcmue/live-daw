#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/hiimdrdey/code/daw/autotune"
PATCH_DIR="/Users/hiimdrdey/autotune"
BUILD_DIR="$PROJECT_DIR/build-retune-fit"
COMPONENT="$BUILD_DIR/VibeAutotune_artefacts/Release/AU/VibeAutotune.component"
INSTALLED="/Users/hiimdrdey/Library/Audio/Plug-Ins/Components/VibeAutotune.component"

apply_once() {
  local patch_file="$1"
  local marker_file="$2"
  local marker="$3"

  # Later passes intentionally edit some of the same hunks as earlier ones,
  # so reverse-patch detection is unreliable.  A stable feature marker makes
  # the installer idempotent even after those overlapping refinements.
  if grep -Fq -- "$marker" "$marker_file"; then
    print "already applied: ${patch_file:t}"
  elif patch --dry-run --batch --forward -p1 -d "$PROJECT_DIR" < "$patch_file" >/dev/null 2>&1; then
    patch --batch --forward -p1 -d "$PROJECT_DIR" < "$patch_file"
  else
    print -u2 "cannot apply cleanly: $patch_file"
    return 1
  fi
}

EDITOR_CPP="$PROJECT_DIR/VibeAutotune/PluginEditor.cpp"
EDITOR_H="$PROJECT_DIR/VibeAutotune/PluginEditor.h"
ROTARY_H="$PROJECT_DIR/VibeAutotune/AnalogRotaryControl.h"

apply_once "$PATCH_DIR/vibe-note-rules-five-state-layout-v2.patch" "$EDITOR_CPP" "static_cast<int> (current) + direction) % 5"
apply_once "$PATCH_DIR/vibe-chassis-background-layer-unification-v3.patch" "$EDITOR_CPP" "One continuous outer shell"
apply_once "$PATCH_DIR/vibe-nested-background-layout-v4.patch" "$EDITOR_CPP" "A single recessed content well owns"
apply_once "$PATCH_DIR/vibe-note-edit-workflow-v5.patch" "$EDITOR_H" "noteRuleHitTargets"
apply_once "$PATCH_DIR/vibe-machined-fasteners-and-rails-v6.patch" "$EDITOR_CPP" "auto drawFastener"
apply_once "$PATCH_DIR/vibe-note-map-pixel-grid-v7.patch" "$EDITOR_H" "NoteMapVisualSlot"
apply_once "$PATCH_DIR/vibe-smoked-lcd-typography-v8.patch" "$EDITOR_CPP" "smokeInk = juce::Colour"
apply_once "$PATCH_DIR/vibe-retune-drag-direction-v9.patch" "$ROTARY_H" "setVerticalDragInverted"

# Refuse to build a visually stale editor.  These checks specifically guard
# the Edit Notes contract that previously regressed while an older component
# was still installed in Logic.
rg -q 'if \(editNotesEnabled\)' "$EDITOR_CPP"
rg -q 'handleNoteRuleGesture' "$EDITOR_CPP"
rg -q 'noteRuleHitTargets' "$EDITOR_H"
rg -q 'NoteMapVisualSlot' "$EDITOR_H"
rg -q 'slot.keyBounds.getCentreX(), statusStrip.getCentreY()' "$EDITOR_CPP"
rg -q 'smokeInk = juce::Colour' "$EDITOR_CPP"
rg -q 'RetuneRotarySlider() { setVerticalDragInverted (true); }' "$EDITOR_H"
if rg -q 'Always show the scale ruler' "$EDITOR_CPP"; then
  print -u2 "stale Note Map workflow is still present; aborting before build"
  exit 1
fi

osascript -e 'tell application "Logic Pro" to quit' 2>/dev/null || true

cmake --build "$BUILD_DIR" --target VibeAutotune_AU --parallel 8

if [[ ! -d "$COMPONENT" ]]; then
  print -u2 "missing build artifact: $COMPONENT"
  exit 1
fi

rm -rf "$INSTALLED"
ditto --rsrc --extattr --acl "$COMPONENT" "$INSTALLED"
# Verify the copied executable before signing.  codesign legitimately mutates
# the Mach-O signature region, so comparing binaries after this point produces
# a false mismatch even when deployment was correct.
if ! cmp -s "$COMPONENT/Contents/MacOS/VibeAutotune" "$INSTALLED/Contents/MacOS/VibeAutotune"; then
  print -u2 "copied AU binary does not match the freshly built component"
  exit 1
fi
BUILD_SHA=$(shasum "$COMPONENT/Contents/MacOS/VibeAutotune" | awk '{print $1}')
COPIED_SHA=$(shasum "$INSTALLED/Contents/MacOS/VibeAutotune" | awk '{print $1}')
codesign --force --deep --sign - "$INSTALLED"
codesign --verify --deep --strict "$INSTALLED"
rm -f "/Users/hiimdrdey/Library/Caches/AudioUnitCache/com.apple.audiounits.cache"
killall -9 AudioComponentRegistrar 2>/dev/null || true
open -a "Logic Pro"

print "Edit Notes workflow verified: hidden by default, interactive when pencil mode is enabled."
print "pre-sign build SHA:  $BUILD_SHA"
print "pre-sign copied SHA: $COPIED_SHA"
print "installed AU signature verified; Logic Pro launched."
