#!/bin/zsh
# Package the already-verified installed VibeAutotune VST3 into the existing
# StudioForge app. This deliberately does NOT build any source tree.
set -euo pipefail

SOURCE_VST3="${VIBE_VERIFIED_VST3:-/Users/hiimdrdey/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3}"
DAW_APP="${STUDIOFORGE_DAW_APP:-/Users/hiimdrdey/Live daw/StudioForge Live DAW.app}"
EMBEDDED_VST3="$DAW_APP/Contents/Resources/PlugIns/VST3/VibeAutotune.vst3"
STAMP=$(date +%Y%m%d-%H%M%S)

source_binary="$SOURCE_VST3/Contents/MacOS/VibeAutotune"
embedded_binary="$EMBEDDED_VST3/Contents/MacOS/VibeAutotune"

[[ -d "$SOURCE_VST3" ]] || { print -u2 "Verified VST3 source is missing: $SOURCE_VST3"; exit 1; }
[[ -f "$source_binary" ]] || { print -u2 "Verified VST3 binary is missing: $source_binary"; exit 1; }
[[ -d "$DAW_APP" ]] || { print -u2 "StudioForge app is missing: $DAW_APP"; exit 1; }

# Refuse an unsigned/broken source rather than package it into the app.
codesign --verify --deep --strict "$SOURCE_VST3"
source_sha=$(shasum -a 256 "$source_binary" | awk '{print $1}')

mkdir -p "${EMBEDDED_VST3:h}"
if [[ -e "$EMBEDDED_VST3" ]]; then
  backup="${EMBEDDED_VST3:r}.backup-$STAMP.vst3"
  mv "$EMBEDDED_VST3" "$backup"
  print "Embedded VST3 backup: $backup"
fi

ditto --rsrc --extattr --acl "$SOURCE_VST3" "$EMBEDDED_VST3"
codesign --force --deep --sign - "$EMBEDDED_VST3"
codesign --verify --deep --strict "$EMBEDDED_VST3"

embedded_sha=$(shasum -a 256 "$embedded_binary" | awk '{print $1}')
[[ "$source_sha" == "$embedded_sha" ]] || {
  print -u2 "Embedded binary SHA mismatch; backup was retained."
  exit 1
}

# The app signature necessarily changes after replacing its bundled VST3.
codesign --force --deep --sign - "$DAW_APP"
codesign --verify --deep --strict "$DAW_APP"
xattr -dr com.apple.quarantine "$DAW_APP" 2>/dev/null || true

print ""
print "PACKAGED VERIFIED VIBEAUTOTUNE INTO STUDIOFORGE"
print "DAW:     $DAW_APP"
print "VST3:    $EMBEDDED_VST3"
print "SHA-256: $embedded_sha"
print "Backup:  ${backup:-none (no prior embedded VST3)}"
print ""
print "Open the app fresh so it releases any cached plug-in instance:"
print "open \"$DAW_APP\""
