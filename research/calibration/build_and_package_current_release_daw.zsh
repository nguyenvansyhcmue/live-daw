#!/bin/zsh
# Build the current StudioForge source as Release, then embed the verified
# already-installed VibeAutotune. This intentionally does not build Vibe.
set -euo pipefail

ROOT="${STUDIOFORGE_ROOT:-/Users/hiimdrdey/code/daw}"
BUILD="${STUDIOFORGE_RELEASE_BUILD_DIR:-$ROOT/build-live-release}"
SOURCE_APP="$BUILD/StudioForgeDAW_artefacts/Release/StudioForge DAW.app"
SOURCE_VST3_PROBE="$BUILD/StudioForgeVst3Probe"
DEST_APP="${STUDIOFORGE_DAW_APP:-/Users/hiimdrdey/Live daw/StudioForge Live DAW.app}"
VERIFIED_VST3="${VIBE_VERIFIED_VST3:-/Users/hiimdrdey/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3}"
STAMP=$(date +%Y%m%d-%H%M%S)

[[ -f "$ROOT/CMakeLists.txt" ]] || { print -u2 "StudioForge source not found: $ROOT"; exit 1; }
[[ -f "$BUILD/CMakeCache.txt" ]] || { print -u2 "Release build cache not found: $BUILD"; exit 1; }
[[ -d "$VERIFIED_VST3" ]] || { print -u2 "Verified VST3 not found: $VERIFIED_VST3"; exit 1; }
codesign --verify --deep --strict "$VERIFIED_VST3"

# Reconfigure using the existing pinned JUCE checkout; do not download or
# substitute dependencies as part of packaging.
JUCE_SOURCE=$(sed -n 's|^FETCHCONTENT_SOURCE_DIR_JUCE:PATH=||p' "$BUILD/CMakeCache.txt")
[[ -d "$JUCE_SOURCE" ]] || { print -u2 "Pinned JUCE source missing: $JUCE_SOURCE"; exit 1; }

cmake -S "$ROOT" -B "$BUILD" -DCMAKE_BUILD_TYPE=Release \
  -DFETCHCONTENT_SOURCE_DIR_JUCE="$JUCE_SOURCE"
cmake --build "$BUILD" --target StudioForgeDAW --parallel 8

[[ -d "$SOURCE_APP" ]] || { print -u2 "Release app was not produced: $SOURCE_APP"; exit 1; }
[[ -f "$SOURCE_VST3_PROBE" ]] || { print -u2 "Release VST3 probe was not produced: $SOURCE_VST3_PROBE"; exit 1; }
source_binary="$VERIFIED_VST3/Contents/MacOS/VibeAutotune"
[[ -f "$source_binary" ]] || { print -u2 "VST3 executable missing: $source_binary"; exit 1; }
source_sha=$(shasum -a 256 "$source_binary" | awk '{print $1}')
release_label="${VIBE_RELEASE_LABEL:-unlabelled}"
release_source="${VIBE_RELEASE_SOURCE:-$VERIFIED_VST3}"
source_daw_binary="$SOURCE_APP/Contents/MacOS/StudioForge DAW"
[[ -f "$source_daw_binary" ]] || { print -u2 "Release DAW executable missing: $source_daw_binary"; exit 1; }
source_daw_sha=$(shasum -a 256 "$source_daw_binary" | awk '{print $1}')

if [[ -e "$DEST_APP" ]]; then
  backup="${DEST_APP:r}.backup-$STAMP.app"
  mv "$DEST_APP" "$backup"
  print "Prior packaged app moved to: $backup"
fi
mkdir -p "${DEST_APP:h}"
ditto --rsrc --extattr --acl "$SOURCE_APP" "$DEST_APP"

embedded="$DEST_APP/Contents/Resources/PlugIns/VST3/VibeAutotune.vst3"
[[ -e "$embedded" ]] && mv "$embedded" "${embedded:r}.backup-$STAMP.vst3"
mkdir -p "${embedded:h}"
ditto --rsrc --extattr --acl "$VERIFIED_VST3" "$embedded"
codesign --force --deep --sign - "$embedded"
codesign --verify --deep --strict "$embedded"

# The VST3 scanner is part of the released host, not a dependency on the
# developer's build directory.  PluginHostService resolves this helper first.
packaged_probe="$DEST_APP/Contents/Resources/Helpers/StudioForgeVst3Probe"
mkdir -p "${packaged_probe:h}"
ditto --rsrc --extattr --acl "$SOURCE_VST3_PROBE" "$packaged_probe"
chmod +x "$packaged_probe"

embedded_sha=$(shasum -a 256 "$embedded/Contents/MacOS/VibeAutotune" | awk '{print $1}')
[[ "$source_sha" == "$embedded_sha" ]] || { print -u2 "Embedded VST3 SHA mismatch"; exit 1; }
[[ -x "$packaged_probe" ]] || { print -u2 "Embedded VST3 scanner helper is missing"; exit 1; }

# Signing alters Mach-O code-signature bytes, so retain the pre-sign Release
# identity as provenance.  The verifier compares this with the current build.
provenance="$DEST_APP/Contents/Resources/StudioForgeBuildProvenance.plist"
rm -f "$provenance"
plutil -create xml1 "$provenance"
plutil -insert sourceDawSHA -string "$source_daw_sha" "$provenance"
plutil -insert embeddedVibeSHA -string "$embedded_sha" "$provenance"
plutil -insert vibeReleaseLabel -string "$release_label" "$provenance"
plutil -insert vibeReleaseSource -string "$release_source" "$provenance"
plutil -insert packagedAtUTC -string "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$provenance"
codesign --force --deep --sign - "$DEST_APP"
codesign --verify --deep --strict "$DEST_APP"
xattr -dr com.apple.quarantine "$DEST_APP" 2>/dev/null || true

print ""
print "CURRENT RELEASE PACKAGED"
print "DAW:     $DEST_APP"
print "VST3:    $embedded"
print "SHA-256: $embedded_sha"
print "Vibe release: $release_label"
print "Release DAW pre-sign SHA-256: $source_daw_sha"
print "Open:    open \"$DEST_APP\""
