#!/bin/zsh
# Read-only release gate for the three deliverables: DAW, VibeAutotune, Tune-AI.
set -euo pipefail

LIVE_ROOT='/Users/hiimdrdey/Live daw'
DAW="$LIVE_ROOT/StudioForge Live DAW.app"
TUNE_APP="$LIVE_ROOT/Tune-AI.app"
TUNE_SOURCE='/Users/hiimdrdey/code/daw/tune-AI'
BUILD_APP='/Users/hiimdrdey/code/daw/build-live-release/StudioForgeDAW_artefacts/Release/StudioForge DAW.app'
INSTALLED_VST3='/Users/hiimdrdey/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3'
EMBEDDED_VST3="$DAW/Contents/Resources/PlugIns/VST3/VibeAutotune.vst3"

fail() { print -u2 "FAIL: $*"; exit 1; }
[[ -d "$DAW" && -d "$TUNE_APP" && -d "$INSTALLED_VST3" && -d "$EMBEDDED_VST3" ]] || fail 'One or more packaged deliverables are missing.'
PROVENANCE="$DAW/Contents/Resources/StudioForgeBuildProvenance.plist"

tree_digest() {
  local root="$1"
  (
    cd "$root"
    find main.py daw_bridge.py core ui assets data native -type f ! -name '.DS_Store' -print0 2>/dev/null \
      | sort -z \
      | while IFS= read -r -d '' file; do
          shasum -a 256 "$file" | awk -v file="$file" '{ print $1 "  " file }'
        done
  )
}

codesign --verify --deep --strict "$DAW" || fail 'DAW signature is invalid.'
codesign --verify --deep --strict "$TUNE_APP" || fail 'Tune-AI signature is invalid.'
codesign --verify --deep --strict "$INSTALLED_VST3" || fail 'Installed VibeAutotune signature is invalid.'
codesign --verify --deep --strict "$EMBEDDED_VST3" || fail 'Embedded VibeAutotune signature is invalid.'

vibe_installed=$(shasum -a 256 "$INSTALLED_VST3/Contents/MacOS/VibeAutotune" | awk '{print $1}')
vibe_embedded=$(shasum -a 256 "$EMBEDDED_VST3/Contents/MacOS/VibeAutotune" | awk '{print $1}')
[[ "$vibe_installed" == "$vibe_embedded" ]] || fail 'DAW embeds a different VibeAutotune binary than the verified installed plug-in.'

[[ -d "$BUILD_APP" ]] || fail "Current Release build is missing: $BUILD_APP"
build_daw=$(shasum -a 256 "$BUILD_APP/Contents/MacOS/StudioForge DAW" | awk '{print $1}')
[[ -f "$PROVENANCE" ]] || fail 'DAW has no release-build provenance; package it again.'
provenance_daw=$(plutil -extract sourceDawSHA raw "$PROVENANCE")
provenance_vibe=$(plutil -extract embeddedVibeSHA raw "$PROVENANCE")
[[ "$build_daw" == "$provenance_daw" ]] || fail 'DAW provenance does not equal the current Release build.'
[[ "$vibe_embedded" == "$provenance_vibe" ]] || fail 'DAW provenance does not equal the embedded Vibe binary.'
provenance_label=$(plutil -extract vibeReleaseLabel raw "$PROVENANCE" 2>/dev/null || true)
provenance_source=$(plutil -extract vibeReleaseSource raw "$PROVENANCE" 2>/dev/null || true)
[[ -n "$provenance_label" && -n "$provenance_source" ]] || fail 'DAW has no identified Vibe release provenance; promote the approved binary again.'

# A current-source release must name the exact source manifest that was built.
# This prevents a self-consistent but historical VST3 from being described as
# the newest plug-in merely because the installed and embedded copies match.
if [[ "$provenance_label" == source-current-* ]]; then
  vibe_source='/Users/hiimdrdey/code/daw-autotune-local-backup-20261017-132903/VibeAutotune'
  [[ -d "$vibe_source" ]] || fail "Current Vibe source is missing: $vibe_source"
  current_vibe_manifest=$(
    cd "${vibe_source:h}"
    find VibeAutotune \( -name build -o -name .git -o -name '.DS_Store' -o -name '*.orig' -o -name '*.rej' \) -prune -o -type f -print0 | sort -z \
      | while IFS= read -r -d '' file; do shasum -a 256 "$file"; done \
      | shasum -a 256 | awk '{print $1}'
  )
  [[ "$provenance_source" == *"manifest-sha256=${current_vibe_manifest}"* ]] \
    || fail 'DAW Vibe release was not built from the current Vibe source manifest.'
fi

[[ -d "$TUNE_SOURCE" ]] || fail "Tune-AI source is missing: $TUNE_SOURCE"
source_tree=$(tree_digest "$TUNE_SOURCE")
package_tree=$(tree_digest "$TUNE_APP/Contents/Resources/tune-AI")
[[ "$source_tree" == "$package_tree" ]] || fail 'Packaged Tune-AI resources differ from current source.'

print 'PASS: current StudioForge ecosystem is internally consistent.'
print "DAW Release SHA-256:       $build_daw (verified before app signing)"
print "Vibe installed/embedded:   $vibe_installed"
print "Vibe approved release:     $provenance_label"
print "Vibe source artifact:      $provenance_source"
print 'Tune-AI source/package:    identical signed resource tree'
print "DAW opens this sibling app: $TUNE_APP"
