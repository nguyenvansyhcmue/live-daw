#!/bin/zsh
set -euo pipefail

ROOT="${STUDIOFORGE_ROOT:-/Users/hiimdrdey/code/daw}"
SCRIPT_DIR="${0:A:h}"
# A monorepo normally keeps Vibe under "$ROOT/autotune", while the preserved
# canonical Vibe workspace is itself the plug-in root.  Allow the release
# orchestrator to state that source root explicitly rather than guessing.
PLUGIN_ROOT="${VIBEAUTOTUNE_SOURCE_ROOT:-$ROOT/autotune}"
VIBE_UI_REFINEMENT_PATCH_FILE="$SCRIPT_DIR/vibe-notemap-legend-refinement.patch"
VIBE_NOTE_CENTRES_PATCH_FILE="$SCRIPT_DIR/vibe-notemap-pixel-centres.patch"
VIBE_METER_REFINEMENT_PATCH_FILE="$SCRIPT_DIR/vibe-meter-hardware-refinement.patch"
VIBE_PIANO_PRESS_PATCH_FILE="$SCRIPT_DIR/vibe-piano-key-press-persistence.patch"
BUILD="${VIBEAUTOTUNE_BUILD_DIR:-$PLUGIN_ROOT/build-studioforge-host}"
DEPENDENCY_ROOT="${VIBEAUTOTUNE_DEPENDENCY_ROOT:-$PLUGIN_ROOT/.third_party}"
LINEAR_SOURCE="$DEPENDENCY_ROOT/signalsmith_linear-src"
STRETCH_SOURCE="$DEPENDENCY_ROOT/signalsmith_stretch-src"
LINEAR_REPOSITORY="https://github.com/Signalsmith-Audio/linear.git"
STRETCH_REPOSITORY="https://github.com/Signalsmith-Audio/signalsmith-stretch.git"
LINEAR_COMMIT="5668673560146a9cfe38c25315071e3fd68c8317"
STRETCH_COMMIT="57b93f4e9206a089a45387eaa39bdc9f310d3308"
AU_SOURCE="$BUILD/VibeAutotune_artefacts/Release/AU/VibeAutotune.component"
VST3_SOURCE="$BUILD/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
AU_DEST="$HOME/Library/Audio/Plug-Ins/Components/VibeAutotune.component"
VST3_DEST="$HOME/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3"
DAW_APP="${STUDIOFORGE_PACKAGED_APP:-/Users/hiimdrdey/Live daw/StudioForge Live DAW.app}"
STAMP=$(date +%Y%m%d-%H%M%S)

[[ -f "$PLUGIN_ROOT/CMakeLists.txt" ]] || { print -u2 "Missing VibeAutotune source: $PLUGIN_ROOT"; exit 1; }
[[ -f "$VIBE_UI_REFINEMENT_PATCH_FILE" ]] || { print -u2 "Missing Vibe UI refinement patch: $VIBE_UI_REFINEMENT_PATCH_FILE"; exit 1; }
[[ -f "$VIBE_NOTE_CENTRES_PATCH_FILE" ]] || { print -u2 "Missing Note Map centre patch: $VIBE_NOTE_CENTRES_PATCH_FILE"; exit 1; }
[[ -f "$VIBE_METER_REFINEMENT_PATCH_FILE" ]] || { print -u2 "Missing meter refinement patch: $VIBE_METER_REFINEMENT_PATCH_FILE"; exit 1; }
[[ -f "$VIBE_PIANO_PRESS_PATCH_FILE" ]] || { print -u2 "Missing piano key-press patch: $VIBE_PIANO_PRESS_PATCH_FILE"; exit 1; }

cd "$ROOT"

# The normal StudioForge layout applies patches from the DAW root.  The
# canonical Vibe workspace is itself the plug-in root, so strip its leading
# `autotune/` path component when applying the same source patch there.
GIT_PATCH_STRIP=0
POSIX_PATCH_STRIP=1
if [[ "$PLUGIN_ROOT" == "$ROOT" ]]; then
  GIT_PATCH_STRIP=2
  POSIX_PATCH_STRIP=2
fi
if git apply --check -p"$GIT_PATCH_STRIP" "$VIBE_UI_REFINEMENT_PATCH_FILE" 2>/dev/null; then
  git apply -p"$GIT_PATCH_STRIP" "$VIBE_UI_REFINEMENT_PATCH_FILE"
  print "Applied: ${VIBE_UI_REFINEMENT_PATCH_FILE:t}"
elif git apply --reverse --check "$VIBE_UI_REFINEMENT_PATCH_FILE" 2>/dev/null; then
  print "Already applied: ${VIBE_UI_REFINEMENT_PATCH_FILE:t}"
elif grep -q 'const auto drawScaleLegend' "$PLUGIN_ROOT/VibeAutotune/PluginEditor.cpp" \
  && grep -q 'D (178, 728, 116, 30)' "$PLUGIN_ROOT/VibeAutotune/PluginEditor.cpp"; then
  print "Already applied (verified by implementation markers): ${VIBE_UI_REFINEMENT_PATCH_FILE:t}"
else
  print -u2 "UI refinement patch does not match the source tree: $VIBE_UI_REFINEMENT_PATCH_FILE"
  exit 1
fi

if git apply --check -p"$GIT_PATCH_STRIP" "$VIBE_NOTE_CENTRES_PATCH_FILE" 2>/dev/null; then
  git apply -p"$GIT_PATCH_STRIP" "$VIBE_NOTE_CENTRES_PATCH_FILE"
  print "Applied: ${VIBE_NOTE_CENTRES_PATCH_FILE:t}"
elif git apply --reverse --check "$VIBE_NOTE_CENTRES_PATCH_FILE" 2>/dev/null; then
  print "Already applied: ${VIBE_NOTE_CENTRES_PATCH_FILE:t}"
elif grep -q 'const auto snapHalfPixel' "$PLUGIN_ROOT/VibeAutotune/PluginEditor.cpp" \
  && grep -q 'slot.keyBounds.setCentre' "$PLUGIN_ROOT/VibeAutotune/PluginEditor.cpp"; then
  print "Already applied (verified by implementation markers): ${VIBE_NOTE_CENTRES_PATCH_FILE:t}"
else
  print -u2 "Note Map centre patch does not match the source tree: $VIBE_NOTE_CENTRES_PATCH_FILE"
  exit 1
fi

# The plug-in subtree is intentionally not tracked by the parent DAW Git
# index, so use the POSIX patch matcher for this source-only visual update.
if patch --batch --forward --dry-run -p"$POSIX_PATCH_STRIP" < "$VIBE_METER_REFINEMENT_PATCH_FILE" >/dev/null 2>&1; then
  patch --batch --forward -p"$POSIX_PATCH_STRIP" < "$VIBE_METER_REFINEMENT_PATCH_FILE"
  print "Applied: ${VIBE_METER_REFINEMENT_PATCH_FILE:t}"
elif grep -q 'auto bezel = juce::ColourGradient' "$PLUGIN_ROOT/VibeAutotune/PluginEditor.cpp" \
  && grep -q 'const auto meterFont' "$PLUGIN_ROOT/VibeAutotune/PluginEditor.cpp" \
  && grep -q 'g.drawHorizontalLine (bottom.getY()' "$PLUGIN_ROOT/VibeAutotune/PluginEditor.cpp"; then
  print "Already applied (verified by implementation markers): ${VIBE_METER_REFINEMENT_PATCH_FILE:t}"
else
  print -u2 "Meter refinement patch does not match the source tree: $VIBE_METER_REFINEMENT_PATCH_FILE"
  exit 1
fi

# Normal Note Map clicks are an explicit UI target. Keep that visual state
# independent of intermittent live tracker frames so a selected key remains
# visibly lit/depressed until it is clicked again.
if grep -q 'int uiSelectedPianoNote = -1' "$PLUGIN_ROOT/VibeAutotune/PluginEditor.h" \
  && grep -q 'const auto isManualSelection' "$PLUGIN_ROOT/VibeAutotune/PluginEditor.cpp"; then
  print "Already applied (verified by implementation markers): ${VIBE_PIANO_PRESS_PATCH_FILE:t}"
elif patch --batch --forward --dry-run -p"$POSIX_PATCH_STRIP" < "$VIBE_PIANO_PRESS_PATCH_FILE" >/dev/null 2>&1; then
  patch --batch --forward -p"$POSIX_PATCH_STRIP" < "$VIBE_PIANO_PRESS_PATCH_FILE"
  print "Applied: ${VIBE_PIANO_PRESS_PATCH_FILE:t}"
else
  print -u2 "Piano key-press patch does not match the source tree: $VIBE_PIANO_PRESS_PATCH_FILE"
  exit 1
fi

# FetchContent source overrides must not live inside a disposable build tree.
# Keep exact, pinned copies here so cleanup and CMake regeneration cannot make
# the canonical VibeAutotune build point at a deleted build/_deps directory.
ensure_pinned_dependency() {
  local name="$1"
  local repository="$2"
  local commit="$3"
  local destination="$4"
  local current=""

  if [[ -d "$destination/.git" ]]; then
    current=$(git -C "$destination" rev-parse HEAD 2>/dev/null || true)
    if [[ "$current" == "$commit" ]]; then
      print "Dependency ready: $name ($commit)"
      return
    fi
  elif [[ -e "$destination" ]]; then
    print -u2 "Dependency path exists but is not a Git checkout: $destination"
    print -u2 "Move that path aside, then run this command again."
    exit 1
  else
    mkdir -p "$destination"
    git -C "$destination" init -q
  fi

  if ! git -C "$destination" remote get-url origin >/dev/null 2>&1; then
    git -C "$destination" remote add origin "$repository"
  fi

  print "Restoring pinned dependency: $name"
  if ! git -C "$destination" fetch --quiet --depth 1 origin "$commit"; then
    print -u2 "Could not download $name from $repository"
    print -u2 "Check the internet connection, then run the same command again."
    exit 1
  fi
  git -C "$destination" checkout --quiet --detach FETCH_HEAD
  current=$(git -C "$destination" rev-parse HEAD)
  [[ "$current" == "$commit" ]] || {
    print -u2 "$name checkout mismatch: expected $commit, got $current"
    exit 1
  }
}

ensure_pinned_dependency "Signalsmith Linear" "$LINEAR_REPOSITORY" "$LINEAR_COMMIT" "$LINEAR_SOURCE"
ensure_pinned_dependency "Signalsmith Stretch" "$STRETCH_REPOSITORY" "$STRETCH_COMMIT" "$STRETCH_SOURCE"

# Always refresh the canonical cache. This overwrites any stale
# FETCHCONTENT_SOURCE_DIR_* values left by an older build without changing the
# generator already selected for BUILD.
print "Configuring latest VibeAutotune..."
cmake -S "$PLUGIN_ROOT" -B "$BUILD" \
  -DCMAKE_BUILD_TYPE=Release \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR="$LINEAR_SOURCE" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH="$STRETCH_SOURCE"

osascript -e 'tell application id "com.StudioForge.StudioForgeDAW" to quit' 2>/dev/null || true
sleep 2

print "Building AU and VST3..."
cmake --build "$BUILD" \
  --target VibeAutotune_AU VibeAutotune_VST3 \
  --parallel 8

[[ -d "$AU_SOURCE" ]] || { print -u2 "AU build artifact missing: $AU_SOURCE"; exit 1; }
[[ -d "$VST3_SOURCE" ]] || { print -u2 "VST3 build artifact missing: $VST3_SOURCE"; exit 1; }

# Sign the exact build artifacts first. Installed binaries then remain byte-for-
# byte identical and can be verified with SHA-256 after copying.
codesign --force --deep --sign - "$AU_SOURCE"
codesign --force --deep --sign - "$VST3_SOURCE"

mkdir -p "${AU_DEST:h}" "${VST3_DEST:h}"
if [[ -e "$AU_DEST" ]]; then
  mv "$AU_DEST" "${AU_DEST:r}.backup-$STAMP.component"
fi
if [[ -e "$VST3_DEST" ]]; then
  mv "$VST3_DEST" "${VST3_DEST:r}.backup-$STAMP.vst3"
fi

ditto --rsrc --extattr --acl "$AU_SOURCE" "$AU_DEST"
ditto --rsrc --extattr --acl "$VST3_SOURCE" "$VST3_DEST"
codesign --verify --deep --strict "$AU_DEST"
codesign --verify --deep --strict "$VST3_DEST"

AU_BUILD_SHA=$(shasum -a 256 "$AU_SOURCE/Contents/MacOS/VibeAutotune" | awk '{print $1}')
AU_INSTALLED_SHA=$(shasum -a 256 "$AU_DEST/Contents/MacOS/VibeAutotune" | awk '{print $1}')
VST3_BUILD_SHA=$(shasum -a 256 "$VST3_SOURCE/Contents/MacOS/VibeAutotune" | awk '{print $1}')
VST3_INSTALLED_SHA=$(shasum -a 256 "$VST3_DEST/Contents/MacOS/VibeAutotune" | awk '{print $1}')

[[ "$AU_BUILD_SHA" == "$AU_INSTALLED_SHA" ]] || { print -u2 "Installed AU does not match latest build"; exit 1; }
[[ "$VST3_BUILD_SHA" == "$VST3_INSTALLED_SHA" ]] || { print -u2 "Installed VST3 does not match latest build"; exit 1; }

# Move caches aside instead of deleting them. StudioForge and Core Audio will
# rebuild metadata from the newly installed binaries.
AU_CACHE="$HOME/Library/Caches/AudioUnitCache/com.apple.audiounits.cache"
PLUGIN_CATALOG="$HOME/Library/Application Support/StudioForge/PluginCatalog.xml"
[[ -e "$AU_CACHE" ]] && mv "$AU_CACHE" "$AU_CACHE.backup-$STAMP"
[[ -e "$PLUGIN_CATALOG" ]] && mv "$PLUGIN_CATALOG" "$PLUGIN_CATALOG.backup-$STAMP"
killall -9 AudioComponentRegistrar 2>/dev/null || true

print "LATEST VIBEAUTOTUNE INSTALLED"
print "AU   SHA-256: $AU_INSTALLED_SHA"
print "VST3 SHA-256: $VST3_INSTALLED_SHA"
print "AU:   $AU_DEST"
print "VST3: $VST3_DEST"

if [[ "${STUDIOFORGE_SKIP_OPEN:-0}" != "1" ]]; then
  [[ -d "$DAW_APP" ]] || { print -u2 "DAW app not found: $DAW_APP"; exit 1; }
  open "$DAW_APP"
fi
