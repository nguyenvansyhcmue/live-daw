#!/bin/zsh
# Build and install the Vibe renderer sibilance guard.  This changes only the
# production Signalsmith renderer; note selection and public parameters stay
# unchanged.  The patch is intentionally refused if the source tree differs.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
BUILD="${VIBE_BUILD:-$VIBE_ROOT/build-studioforge-juce8-stable}"
SCRIPT_DIR="${0:A:h}"
PATCH_FILE="$SCRIPT_DIR/vibe-signalsmith-sibilance-transparency.patch"
DETECTOR_V2_PATCH="$SCRIPT_DIR/vibe-signalsmith-sibilance-detector-v2.patch"
UNVOICED_V3_PATCH="$SCRIPT_DIR/vibe-signalsmith-sibilance-unvoiced-v3.patch"
SOURCE_BUNDLE="$BUILD/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
DEST_BUNDLE="$HOME/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3"
STAMP=$(date +%Y%m%d-%H%M%S)

[[ -f "$VIBE_ROOT/CMakeLists.txt" ]] || { print -u2 "Missing Vibe source: $VIBE_ROOT"; exit 66; }
[[ -f "$PATCH_FILE" ]] || { print -u2 "Missing patch: $PATCH_FILE"; exit 66; }

if ! rg -q 'sibilanceTargetDelay' "$VIBE_ROOT/VibeAutotune/SignalsmithPitchRenderer.h"; then
    patch -d "$VIBE_ROOT" -p1 --dry-run --batch < "$PATCH_FILE"
    patch -d "$VIBE_ROOT" -p1 --batch < "$PATCH_FILE"
else
    print "Sibilance guard already present in source."
fi

if ! rg -q 'sourceAnalysisCrossoverHz' "$VIBE_ROOT/VibeAutotune/SignalsmithPitchRenderer.h"; then
    patch -d "$VIBE_ROOT" -p1 --dry-run --batch < "$DETECTOR_V2_PATCH"
    patch -d "$VIBE_ROOT" -p1 --batch < "$DETECTOR_V2_PATCH"
else
    print "Sibilance detector v2 already present in source."
fi

if ! rg -q 'sibilanceDeEssDepth' "$VIBE_ROOT/VibeAutotune/SignalsmithPitchRenderer.h"; then
    patch -d "$VIBE_ROOT" -p1 --dry-run --batch < "$UNVOICED_V3_PATCH"
    patch -d "$VIBE_ROOT" -p1 --batch < "$UNVOICED_V3_PATCH"
else
    print "Unvoiced sibilance protection already present in source."
fi

cmake --build "$BUILD" \
    --target VibeAutotuneSignalsmithRendererTest VibeAutotune_VST3 \
    --parallel 8
"$BUILD/VibeAutotuneSignalsmithRendererTest"

[[ -f "$SOURCE_BUNDLE/Contents/MacOS/VibeAutotune" ]] || {
    print -u2 "Missing built VST3: $SOURCE_BUNDLE"; exit 1
}

/usr/bin/codesign --force --deep --sign - "$SOURCE_BUNDLE"
/usr/bin/codesign --verify --deep --strict --verbose=2 "$SOURCE_BUNDLE"

if [[ -d "$DEST_BUNDLE" ]]; then
    mv "$DEST_BUNDLE" "${DEST_BUNDLE%.vst3}.backup-$STAMP.vst3"
fi
mkdir -p "${DEST_BUNDLE:h}"
ditto --rsrc --extattr --acl "$SOURCE_BUNDLE" "$DEST_BUNDLE"
/usr/bin/codesign --force --deep --sign - "$DEST_BUNDLE"
/usr/bin/codesign --verify --deep --strict --verbose=2 "$DEST_BUNDLE"

BUILD_SHA=$(shasum "$SOURCE_BUNDLE/Contents/MacOS/VibeAutotune" | awk '{print $1}')
INSTALLED_SHA=$(shasum "$DEST_BUNDLE/Contents/MacOS/VibeAutotune" | awk '{print $1}')
[[ "$BUILD_SHA" == "$INSTALLED_SHA" ]] || { print -u2 "Installed VST3 binary differs from build"; exit 1; }

print ""
print "Installed VibeAutotune VST3 with latency-aligned sibilance transparency."
print "Restart StudioForge before the next A/B run."
print "Then run: zsh $SCRIPT_DIR/run_hook2_artist_vibe_baseline.zsh"
