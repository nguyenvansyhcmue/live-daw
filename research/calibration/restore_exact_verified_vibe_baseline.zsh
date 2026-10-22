#!/bin/zsh
# Restore the exact Vibe binary that was measured in the annotated-fricative
# verification.  This is intentionally a binary-baseline restore, not an
# invented "source merge": a VST3 cannot be reliably decompiled into the C++
# source that produced it.
set -euo pipefail

TOOLS_ROOT='/Users/hiimdrdey/autotune'
DAW_ROOT='/Users/hiimdrdey/code/daw'
APP='/Users/hiimdrdey/Live daw/StudioForge Live DAW.app'
INSTALLED='/Users/hiimdrdey/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3'
BASELINE='/Users/hiimdrdey/Library/Audio/Plug-Ins/VST3/VibeAutotune.before-approved-20261019-011508.vst3'
EXPECTED_SHA='0eea517d9e1647d0d848f08702742a8ef034fe5f72921c16b8124ef91f6c0a63'
STAMP=$(date +%Y%m%d-%H%M%S)

[[ -d "$BASELINE" ]] || { print -u2 "Missing preserved verified baseline: $BASELINE"; exit 1; }
if pgrep -x 'StudioForge DAW' >/dev/null 2>&1; then
  print -u2 'Quit StudioForge DAW completely before replacing its bundled plug-in.'
  exit 2
fi

baseline_binary="$BASELINE/Contents/MacOS/VibeAutotune"
[[ -f "$baseline_binary" ]] || { print -u2 'Baseline VST3 has no executable.'; exit 1; }
baseline_sha=$(shasum -a 256 "$baseline_binary" | awk '{print $1}')
[[ "$baseline_sha" == "$EXPECTED_SHA" ]] || {
  print -u2 "Wrong baseline binary: expected $EXPECTED_SHA, found $baseline_sha"
  exit 1
}
codesign --verify --deep --strict "$BASELINE"

if [[ -d "$INSTALLED" ]]; then
  mv "$INSTALLED" "${INSTALLED:r}.before-verified-baseline-$STAMP.vst3"
fi
ditto --rsrc --extattr --acl "$BASELINE" "$INSTALLED"
codesign --force --deep --sign - "$INSTALLED"
codesign --verify --deep --strict "$INSTALLED"

VIBE_VERIFIED_VST3="$INSTALLED" \
VIBE_RELEASE_LABEL='verified-binary-baseline-2026-10-19' \
VIBE_RELEASE_SOURCE="preserved verified binary $BASELINE; source snapshot unavailable; sha256=$EXPECTED_SHA" \
  zsh "$TOOLS_ROOT/build_and_package_current_release_daw.zsh"
zsh "$TOOLS_ROOT/repair_studioforge_vibe_catalog.zsh"

embedded="$APP/Contents/Resources/PlugIns/VST3/VibeAutotune.vst3/Contents/MacOS/VibeAutotune"
[[ -f "$embedded" ]] || { print -u2 'Packaged DAW does not contain VibeAutotune.'; exit 1; }
embedded_sha=$(shasum -a 256 "$embedded" | awk '{print $1}')
[[ "$embedded_sha" == "$EXPECTED_SHA" ]] || { print -u2 "Embedded baseline SHA mismatch: $embedded_sha"; exit 1; }

print ''
print 'EXACT VERIFIED BASELINE RESTORED'
print "Vibe SHA-256: $EXPECTED_SHA"
print 'This is the VST3 measured by the Oct-19 annotated-fricative verification.'
print 'It is now both installed and bundled in the packaged DAW.'
print "Open: open '$APP'"
