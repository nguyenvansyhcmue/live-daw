#!/bin/zsh
# Restore the bounded voiced-only guard after the v3 unvoiced experiment.
# v3 over-attenuated unrelated high-energy material in the hook2 A/B run.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
BUILD="${VIBE_BUILD:-$VIBE_ROOT/build-studioforge-juce8-stable}"
SCRIPT_DIR="${0:A:h}"
PATCH_FILE="$SCRIPT_DIR/revert-vibe-sibilance-unvoiced-v3.patch"
SOURCE_BUNDLE="$BUILD/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
DEST_BUNDLE="$HOME/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3"
STAMP=$(date +%Y%m%d-%H%M%S)

[[ -f "$VIBE_ROOT/CMakeLists.txt" && -f "$PATCH_FILE" ]] || { print -u2 "Missing source or revert patch"; exit 66; }
if rg -q 'sibilanceDeEssDepth' "$VIBE_ROOT/VibeAutotune/SignalsmithPitchRenderer.h"; then
    patch -d "$VIBE_ROOT" -p1 --dry-run --batch < "$PATCH_FILE"
    patch -d "$VIBE_ROOT" -p1 --batch < "$PATCH_FILE"
else
    print "v3 unvoiced experiment is not present; nothing to revert."
fi

cmake --build "$BUILD" --target VibeAutotuneSignalsmithRendererTest VibeAutotune_VST3 --parallel 8
"$BUILD/VibeAutotuneSignalsmithRendererTest"
[[ -f "$SOURCE_BUNDLE/Contents/MacOS/VibeAutotune" ]] || { print -u2 "Missing built VST3"; exit 1; }
/usr/bin/codesign --force --deep --sign - "$SOURCE_BUNDLE"
if [[ -d "$DEST_BUNDLE" ]]; then
    mv "$DEST_BUNDLE" "${DEST_BUNDLE%.vst3}.backup-$STAMP.vst3"
fi
mkdir -p "${DEST_BUNDLE:h}"
ditto --rsrc --extattr --acl "$SOURCE_BUNDLE" "$DEST_BUNDLE"
/usr/bin/codesign --force --deep --sign - "$DEST_BUNDLE"
/usr/bin/codesign --verify --deep --strict --verbose=2 "$DEST_BUNDLE"
print "Restored bounded sibilance guard. Restart StudioForge."
