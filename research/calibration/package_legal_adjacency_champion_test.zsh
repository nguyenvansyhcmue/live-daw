#!/bin/zsh
# Package the one accepted-but-unmerged Vibe research champion for listening.
# This is explicitly a reversible research A/B package, not a production
# promotion. The script preserves the previously installed VST3 and DAW app.
set -euo pipefail

TOOLS_ROOT='/Users/hiimdrdey/autotune'
APP='/Users/hiimdrdey/Live daw/StudioForge Live DAW.app'
INSTALLED='/Users/hiimdrdey/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3'
CANDIDATE='/Users/hiimdrdey/autotune/artifacts/crossing24-bounded-preview-20261017-113341/source/build-legal-adjacency-eval/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3'
EXPECTED_SHA='64e935b9a09239e8db917d6c193d5d5c1709ee7b7d54dd737c915cd9b51b575e'
STAMP=$(date +%Y%m%d-%H%M%S)

[[ -d "$CANDIDATE" ]] || { print -u2 "Missing legal-adjacency champion: $CANDIDATE"; exit 1; }
if pgrep -x 'StudioForge DAW' >/dev/null 2>&1; then
  print -u2 'Quit StudioForge DAW completely before replacing its bundled plug-in.'
  exit 2
fi
candidate_binary="$CANDIDATE/Contents/MacOS/VibeAutotune"
candidate_sha=$(shasum -a 256 "$candidate_binary" | awk '{print $1}')
[[ "$candidate_sha" == "$EXPECTED_SHA" ]] || {
  print -u2 "Wrong candidate binary: expected $EXPECTED_SHA, found $candidate_sha"
  exit 1
}

if [[ -d "$INSTALLED" ]]; then
  mv "$INSTALLED" "${INSTALLED:r}.before-legal-adjacency-test-$STAMP.vst3"
fi
ditto --rsrc --extattr --acl "$CANDIDATE" "$INSTALLED"
# The artifact's old ad-hoc signature is intentionally refreshed after the
# verified bytes are copied; signing necessarily changes the executable hash,
# while the pre-sign SHA is retained in the DAW provenance below.
codesign --force --deep --sign - "$INSTALLED"
codesign --verify --deep --strict "$INSTALLED"

VIBE_VERIFIED_VST3="$INSTALLED" \
VIBE_RELEASE_LABEL='research-legal-scale-adjacency-champion-2026-10-19' \
VIBE_RELEASE_SOURCE="pre-sign-sha256=$EXPECTED_SHA; accepted Hook-2 legal-scale adjacency + 24ms crossing; research A/B only" \
  zsh "$TOOLS_ROOT/build_and_package_current_release_daw.zsh"
zsh "$TOOLS_ROOT/repair_studioforge_vibe_catalog.zsh"

embedded="$APP/Contents/Resources/PlugIns/VST3/VibeAutotune.vst3/Contents/MacOS/VibeAutotune"
[[ -f "$embedded" ]] || { print -u2 'Packaged DAW does not contain VibeAutotune.'; exit 1; }
embedded_sha=$(shasum -a 256 "$embedded" | awk '{print $1}')

print ''
print 'LEGAL-ADJACENCY CHAMPION TEST PACKAGED'
print "Candidate pre-sign SHA: $EXPECTED_SHA"
print "Installed/embedded SHA after ad-hoc signing: $embedded_sha"
print 'Status: accepted research champion, unmerged; test it against Artist before production promotion.'
print "Open: open '$APP'"
