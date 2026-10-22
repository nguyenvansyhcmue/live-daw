#!/bin/zsh
# Build the current VibeAutotune source, install that exact binary, and embed
# it in the current StudioForge release. Research snapshots and preserved
# historical VST3s are never selected merely because they exist on disk.
set -euo pipefail

TOOLS_ROOT='/Users/hiimdrdey/autotune'
DAW_ROOT='/Users/hiimdrdey/code/daw'
PLUGIN_BUILD_ROOT='/Users/hiimdrdey/code/daw-autotune-local-backup-20261017-132903'
FRESH_VIBE_BUILD="$TOOLS_ROOT/build-current-source-release"
VIBE_SOURCE="$DAW_ROOT/autotune/VibeAutotune"
INSTALLED='/Users/hiimdrdey/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3'

[[ -f "$DAW_ROOT/CMakeLists.txt" ]] || { print -u2 "StudioForge source is missing: $DAW_ROOT"; exit 1; }
[[ -f "$PLUGIN_BUILD_ROOT/CMakeLists.txt" ]] || { print -u2 "Complete Vibe build root is missing: $PLUGIN_BUILD_ROOT"; exit 1; }
[[ -f "$VIBE_SOURCE/PluginProcessor.cpp" ]] || { print -u2 "Vibe source is missing: $VIBE_SOURCE"; exit 1; }
[[ -f "$PLUGIN_BUILD_ROOT/VibeAutotune/PluginProcessor.cpp" ]] || { print -u2 "Complete Vibe source is missing: $PLUGIN_BUILD_ROOT"; exit 1; }

# Replacing a plug-in under a running host is unsafe and can leave old code
# mapped in memory. Save work and quit StudioForge before this release step.
if pgrep -x 'StudioForge DAW' >/dev/null 2>&1; then
  print -u2 'StudioForge DAW is still running. Save, quit it completely, then rerun this release command.'
  exit 2
fi

# Fingerprint the actual source inputs before compilation. This keeps a
# packaged release auditable even when the DAW source tree has local changes.
source_manifest=$(
  cd "$DAW_ROOT/autotune"
  find VibeAutotune \( -name build -o -name .git -o -name '.DS_Store' -o -name '*.orig' -o -name '*.rej' \) -prune -o -type f -print0 | sort -z \
    | while IFS= read -r -d '' file; do shasum -a 256 "$file"; done \
    | shasum -a 256 | awk '{print $1}'
)
build_source_manifest=$(
  cd "$PLUGIN_BUILD_ROOT"
  find VibeAutotune \( -name build -o -name .git -o -name '.DS_Store' -o -name '*.orig' -o -name '*.rej' \) -prune -o -type f -print0 \
    | sort -z | while IFS= read -r -d '' file; do shasum -a 256 "$file"; done \
    | shasum -a 256 | awk '{print $1}'
)
[[ "$source_manifest" == "$build_source_manifest" ]] || {
  print -u2 'Monorepo Vibe source does not equal the complete build source; refusing to release an ambiguous revision.'
  exit 1
}
source_commit=$(git -C "$PLUGIN_BUILD_ROOT" rev-parse --short=12 HEAD 2>/dev/null || print 'unversioned')
source_dirty='clean'
git -C "$PLUGIN_BUILD_ROOT" diff --quiet -- VibeAutotune 2>/dev/null || source_dirty='dirty'
release_label="source-current-${source_commit}-${source_dirty}"
release_source="${PLUGIN_BUILD_ROOT}/VibeAutotune; build-root=${PLUGIN_BUILD_ROOT}"

print 'Building VibeAutotune from the current DAW source tree...'
STUDIOFORGE_ROOT="$PLUGIN_BUILD_ROOT" \
VIBEAUTOTUNE_SOURCE_ROOT="$PLUGIN_BUILD_ROOT" \
VIBEAUTOTUNE_BUILD_DIR="$FRESH_VIBE_BUILD" \
STUDIOFORGE_SKIP_OPEN=1 \
  zsh "$TOOLS_ROOT/deploy_latest_vibeautotune_to_daw.zsh"

[[ -d "$INSTALLED" ]] || { print -u2 'Current-source VST3 was not installed.'; exit 1; }
codesign --verify --deep --strict "$INSTALLED"
installed_sha=$(shasum -a 256 "$INSTALLED/Contents/MacOS/VibeAutotune" | awk '{print $1}')
[[ -n "$installed_sha" ]] || { print -u2 'Cannot identify installed Vibe binary.'; exit 1; }

# The deployment step may apply the approved UI persistence patch. Record the
# manifest after that step, because it is the precise source revision built.
compiled_source_manifest=$(
  cd "$PLUGIN_BUILD_ROOT"
  find VibeAutotune \( -name build -o -name .git -o -name '.DS_Store' -o -name '*.orig' -o -name '*.rej' \) -prune -o -type f -print0 \
    | sort -z | while IFS= read -r -d '' file; do shasum -a 256 "$file"; done \
    | shasum -a 256 | awk '{print $1}'
)
release_source="${release_source}; manifest-sha256=${compiled_source_manifest}"

VIBE_VERIFIED_VST3="$INSTALLED" \
VIBE_RELEASE_LABEL="$release_label" \
VIBE_RELEASE_SOURCE="$release_source" \
  zsh "$TOOLS_ROOT/build_and_package_current_release_daw.zsh"

zsh "$TOOLS_ROOT/repair_studioforge_vibe_catalog.zsh"
zsh "$TOOLS_ROOT/verify_current_studioforge_ecosystem.zsh"

print ''
print 'CURRENT-SOURCE RELEASE COMPLETE: Vibe was rebuilt, installed, and embedded.'
print "Vibe SHA-256: $installed_sha"
print "Source manifest SHA-256: $compiled_source_manifest"
print "Source revision: $source_commit ($source_dirty)"
print 'Next: zsh /Users/hiimdrdey/autotune/open_current_studioforge_with_trace.zsh'
