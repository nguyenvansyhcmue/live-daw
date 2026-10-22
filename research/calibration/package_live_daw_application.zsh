#!/bin/zsh
set -euo pipefail

ROOT="${STUDIOFORGE_ROOT:-/Users/hiimdrdey/code/daw}"
SCRIPT_DIR="${0:A:h}"
PATCH_FILE="$SCRIPT_DIR/studioforge-tune-ai-live-workflow.patch"
PACKAGE_PATCH_FILE="$SCRIPT_DIR/studioforge-packaged-tune-ai.patch"
FULL_UI_PATCH_FILE="$SCRIPT_DIR/studioforge-autokey-full-ui.patch"
LATEST_VIBE_PATCH_FILE="$SCRIPT_DIR/studioforge-latest-vibe-only.patch"
FX_SLOT_PATCH_FILE="$SCRIPT_DIR/studioforge-fx-slot-interaction.patch"
VIBE_UI_REFINEMENT_PATCH_FILE="$SCRIPT_DIR/vibe-notemap-legend-refinement.patch"
VIBE_NOTE_CENTRES_PATCH_FILE="$SCRIPT_DIR/vibe-notemap-pixel-centres.patch"
LIVE_VIBE_HEALTH_PATCH_FILE="$SCRIPT_DIR/studioforge-live-vibe-health-gate.patch"
LIVE_VIBE_AUDIBILITY_PATCH_FILE="$SCRIPT_DIR/studioforge-live-vibe-audibility-invariant.patch"
BUILD="${STUDIOFORGE_RELEASE_BUILD_DIR:-$ROOT/build-live-release}"
PACKAGE_DIR="${STUDIOFORGE_PACKAGE_DIR:-/Users/hiimdrdey/Live daw}"
DEST_APP="$PACKAGE_DIR/StudioForge Live DAW.app"
TUNE_SOURCE="$ROOT/tune-AI"
TUNE_APP="$PACKAGE_DIR/Tune-AI.app"

[[ -f "$ROOT/CMakeLists.txt" ]] || { print -u2 "Missing StudioForge source: $ROOT"; exit 1; }
[[ -f "$PATCH_FILE" ]] || { print -u2 "Missing workflow patch: $PATCH_FILE"; exit 1; }
[[ -f "$PACKAGE_PATCH_FILE" ]] || { print -u2 "Missing packaged Tune-AI patch: $PACKAGE_PATCH_FILE"; exit 1; }
[[ -f "$FULL_UI_PATCH_FILE" ]] || { print -u2 "Missing full Tune-AI UI routing patch: $FULL_UI_PATCH_FILE"; exit 1; }
[[ -f "$LATEST_VIBE_PATCH_FILE" ]] || { print -u2 "Missing latest-only VibeAutotune patch: $LATEST_VIBE_PATCH_FILE"; exit 1; }
[[ -f "$FX_SLOT_PATCH_FILE" ]] || { print -u2 "Missing FX slot interaction patch: $FX_SLOT_PATCH_FILE"; exit 1; }
[[ -f "$VIBE_UI_REFINEMENT_PATCH_FILE" ]] || { print -u2 "Missing Vibe UI refinement patch: $VIBE_UI_REFINEMENT_PATCH_FILE"; exit 1; }
[[ -f "$VIBE_NOTE_CENTRES_PATCH_FILE" ]] || { print -u2 "Missing Note Map centre patch: $VIBE_NOTE_CENTRES_PATCH_FILE"; exit 1; }
[[ -f "$LIVE_VIBE_HEALTH_PATCH_FILE" ]] || { print -u2 "Missing live Vibe health patch: $LIVE_VIBE_HEALTH_PATCH_FILE"; exit 1; }
[[ -f "$LIVE_VIBE_AUDIBILITY_PATCH_FILE" ]] || { print -u2 "Missing live Vibe audibility patch: $LIVE_VIBE_AUDIBILITY_PATCH_FILE"; exit 1; }
[[ -f "$TUNE_SOURCE/main.py" ]] || { print -u2 "Missing Tune-AI UI source: $TUNE_SOURCE"; exit 1; }
[[ -x "$TUNE_SOURCE/.venv/bin/python3" ]] || { print -u2 "Missing Tune-AI Python runtime: $TUNE_SOURCE/.venv"; exit 1; }

cd "$ROOT"

patch_is_semantically_applied() {
  case "${1:t}" in
    studioforge-tune-ai-live-workflow.patch)
      grep -q 'onAutoKeyRequested' "$ROOT/Source/UI/ControlBar.h" \
        && grep -q 'beginBeatKeyLearning' "$ROOT/Source/UI/MainComponent.cpp" \
        && grep -q 'resetLiveKeyDetection' "$ROOT/Source/AudioEngine/AudioEngine.h"
      ;;
    studioforge-packaged-tune-ai.patch)
      grep -q 'findPackagedTuneAiBundle' "$ROOT/Source/Services/TuneAiAnalysisService.cpp" \
        && grep -q 'packagedTuneAiRoot' "$ROOT/Source/Services/TuneAiAnalysisService.cpp"
      ;;
    studioforge-autokey-full-ui.patch)
      ! grep -q 'Source/UI/TuneAiPanel.cpp' "$ROOT/CMakeLists.txt" \
        && ! grep -q 'TuneAiPanel' "$ROOT/Source/UI/MainComponent.cpp" \
        && grep -q 'launchStandaloneApp' "$ROOT/Source/UI/MainComponent.cpp"
      ;;
    studioforge-latest-vibe-only.patch)
      grep -q 'canonical VST3' "$ROOT/Source/Control/PitchCorrectionIntegrationService.cpp" \
        && grep -q 'previousState' "$ROOT/Source/Control/PitchCorrectionIntegrationService.cpp"
      ;;
    studioforge-fx-slot-interaction.patch)
      grep -q 'class AudioFxSlotButton' "$ROOT/Source/UI/InspectorComponents.h" \
        && grep -q 'Replace Plug-in' "$ROOT/Source/UI/InspectorComponents.cpp" \
        && grep -q 'click to bypass' "$ROOT/Source/UI/InspectorComponents.cpp"
      ;;
    vibe-notemap-legend-refinement.patch)
      grep -q 'const auto drawScaleLegend' "$ROOT/autotune/VibeAutotune/PluginEditor.cpp" \
        && grep -q 'D (178, 728, 116, 30)' "$ROOT/autotune/VibeAutotune/PluginEditor.cpp" \
        && grep -q 'N(65,728,105,30)' "$ROOT/autotune/VibeAutotune/PluginEditor.cpp"
      ;;
    vibe-notemap-pixel-centres.patch)
      grep -q 'const auto snapHalfPixel' "$ROOT/autotune/VibeAutotune/PluginEditor.cpp" \
        && grep -q 'slot.keyBounds.setCentre' "$ROOT/autotune/VibeAutotune/PluginEditor.cpp"
      ;;
    studioforge-live-vibe-health-gate.patch)
      grep -q 'LiveProcessorHealth getLiveProcessorHealth' "$ROOT/Source/Plugins/NativeVibeAutotuneProcessor.h" \
        && grep -q 'latency-aligned dry stream' "$ROOT/Source/Plugins/NativeVibeAutotuneProcessor.cpp" \
        && grep -q 'TRACKING — tuned renderer is healthy' "$ROOT/Source/UI/InspectorComponents.cpp"
      ;;
    studioforge-live-vibe-audibility-invariant.patch)
      grep -q 'Final live-audibility invariant' "$ROOT/Source/Plugins/NativeVibeAutotuneProcessor.cpp" \
        && grep -q 'hardDryRescue' "$ROOT/Source/Plugins/NativeVibeAutotuneProcessor.cpp"
      ;;
    *) return 1 ;;
  esac
}

for patch_file in "$PATCH_FILE" "$PACKAGE_PATCH_FILE" "$FULL_UI_PATCH_FILE" "$LATEST_VIBE_PATCH_FILE" "$FX_SLOT_PATCH_FILE" "$VIBE_UI_REFINEMENT_PATCH_FILE" "$VIBE_NOTE_CENTRES_PATCH_FILE" "$LIVE_VIBE_HEALTH_PATCH_FILE" "$LIVE_VIBE_AUDIBILITY_PATCH_FILE"; do
  if git apply --check --recount "$patch_file" 2>/dev/null; then
    git apply --recount "$patch_file"
    print "Applied: ${patch_file:t}"
  elif git apply --reverse --check --recount "$patch_file" 2>/dev/null; then
    print "Already applied: ${patch_file:t}"
  elif patch_is_semantically_applied "$patch_file"; then
    print "Already applied (verified by implementation markers): ${patch_file:t}"
  else
    print -u2 "Patch does not match the source tree: $patch_file"
    exit 1
  fi
done

if [[ ! -f "$BUILD/CMakeCache.txt" ]]; then
  typeset -a configure_args
  configure_args=(
    -S "$ROOT"
    -B "$BUILD"
    -G Ninja
    -DCMAKE_BUILD_TYPE=Release
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    -DBUILD_TESTING=ON
  )

  # Reuse the already downloaded JUCE checkout, so packaging does not depend
  # on GitHub or repeat the previous FetchContent download failure.
  for juce_source in \
    "$ROOT/build-macos-arm64/_deps/juce-src" \
    "$ROOT/build-calibration-arm64/_deps/juce-src"; do
    if [[ -d "$juce_source" ]]; then
      configure_args+=("-DFETCHCONTENT_SOURCE_DIR_JUCE=$juce_source")
      break
    fi
  done

  cmake "${configure_args[@]}"
fi

print "Deploying the latest VibeAutotune plug-in..."
STUDIOFORGE_ROOT="$ROOT" STUDIOFORGE_SKIP_OPEN=1 \
  zsh "$SCRIPT_DIR/deploy_latest_vibeautotune_to_daw.zsh"

print "Building StudioForge DAW and live-safety tests..."
cmake --build "$BUILD" --target StudioForgeDAW StudioForgeNativeVibeSmokeTest --parallel 8
print "Running StudioForgeNativeVibeSmokeTest..."
"$BUILD/StudioForgeNativeVibeSmokeTest"
print "Live-safety smoke test passed. Packaging applications..."

SOURCE_APP="$BUILD/StudioForgeDAW_artefacts/Release/StudioForge DAW.app"
[[ -d "$SOURCE_APP" ]] || { print -u2 "Release app was not produced: $SOURCE_APP"; exit 1; }

mkdir -p "$PACKAGE_DIR"
if [[ -e "$DEST_APP" ]]; then
  BACKUP_APP="$PACKAGE_DIR/StudioForge Live DAW backup $(date +%Y%m%d-%H%M%S).app"
  mv "$DEST_APP" "$BACKUP_APP"
  print "Previous package moved to: $BACKUP_APP"
fi

ditto --rsrc --extattr --acl "$SOURCE_APP" "$DEST_APP"
INFO_PLIST="$DEST_APP/Contents/Info.plist"
if [[ -f "$INFO_PLIST" ]]; then
  /usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName StudioForge Live DAW" "$INFO_PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string 'StudioForge Live DAW'" "$INFO_PLIST"
  /usr/libexec/PlistBuddy -c "Set :CFBundleName StudioForge Live DAW" "$INFO_PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleName string 'StudioForge Live DAW'" "$INFO_PLIST"
fi

codesign --force --deep --sign - "$DEST_APP"
xattr -dr com.apple.quarantine "$DEST_APP" 2>/dev/null || true
codesign --verify --deep --strict "$DEST_APP"

if [[ -e "$TUNE_APP" ]]; then
  TUNE_BACKUP="$PACKAGE_DIR/Tune-AI backup $(date +%Y%m%d-%H%M%S).app"
  mv "$TUNE_APP" "$TUNE_BACKUP"
  print "Previous Tune-AI package moved to: $TUNE_BACKUP"
fi

mkdir -p "$TUNE_APP/Contents/MacOS" "$TUNE_APP/Contents/Resources/tune-AI"
ditto "$SCRIPT_DIR/Tune-AI-Info.plist" "$TUNE_APP/Contents/Info.plist"
ditto "$SCRIPT_DIR/tune_ai_macos_launcher.zsh" "$TUNE_APP/Contents/MacOS/Tune-AI"
chmod +x "$TUNE_APP/Contents/MacOS/Tune-AI"

# Copy the actual custom Tune-AI interface and its working runtime. Development
# caches, old virtual environments and tests are deliberately not packaged.
for item in main.py daw_bridge.py core ui assets data native; do
  if [[ -e "$TUNE_SOURCE/$item" ]]; then
    ditto "$TUNE_SOURCE/$item" "$TUNE_APP/Contents/Resources/tune-AI/$item"
  fi
done
ditto "$TUNE_SOURCE/.venv" "$TUNE_APP/Contents/Resources/tune-AI/.venv"

# A venv normally points python3.11 to Homebrew using an absolute symlink.
# Absolute links escaping a macOS .app are rejected by codesign. Embed the
# resolved interpreter at that exact location; the remaining python/python3
# links are relative and stay entirely inside the bundle.
REAL_PYTHON=$("$TUNE_SOURCE/.venv/bin/python3" -c 'import os, sys; print(os.path.realpath(sys.executable))')
PACKAGED_PYTHON="$TUNE_APP/Contents/Resources/tune-AI/.venv/bin/python3.11"
[[ -f "$REAL_PYTHON" ]] || { print -u2 "Could not resolve Tune-AI Python interpreter"; exit 1; }
if [[ -L "$PACKAGED_PYTHON" ]]; then
  unlink "$PACKAGED_PYTHON"
fi
ditto "$REAL_PYTHON" "$PACKAGED_PYTHON"
chmod +x "$PACKAGED_PYTHON"

# Refuse to sign a broken package instead of leaving another unusable app.
while IFS= read -r link; do
  target=$(readlink "$link")
  if [[ "$target" == /* ]]; then
    print -u2 "External symlink remains in Tune-AI.app: $link -> $target"
    exit 1
  fi
done < <(find "$TUNE_APP" -type l -print)

codesign --force --deep --sign - "$TUNE_APP"
xattr -dr com.apple.quarantine "$TUNE_APP" 2>/dev/null || true
codesign --verify --deep --strict "$TUNE_APP"

print ""
print "PACKAGED: $DEST_APP"
print "PACKAGED: $TUNE_APP (your full custom Tune-AI interface)"
print "AUTO KEY: use the AUTO KEY button, then OPEN FULL TUNE-AI; the DAW resolves this packaged app first."
print "Opening both packaged applications..."
open "$DEST_APP"
open "$TUNE_APP"
