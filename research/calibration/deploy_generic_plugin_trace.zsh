#!/bin/zsh
set -euo pipefail

# Adds evidence only: it does not alter plug-in DSP, routing, PDC or presets.
ROOT="${STUDIOFORGE_ROOT:-/Users/hiimdrdey/code/daw}"
SCRIPT_DIR="${0:A:h}"
PATCH_FILE="$SCRIPT_DIR/studioforge-generic-plugin-processing-trace.patch"
CSV_ALIGNMENT_PATCH_FILE="$SCRIPT_DIR/studioforge-generic-plugin-trace-csv-alignment.patch"
BUILD="${STUDIOFORGE_RELEASE_BUILD_DIR:-$ROOT/build-live-release}"
SOURCE_APP="$BUILD/StudioForgeDAW_artefacts/Release/StudioForge DAW.app"
DEST_DIR="${STUDIOFORGE_PACKAGE_DIR:-/Users/hiimdrdey/Live daw}"
DEST_APP="$DEST_DIR/StudioForge Live DAW.app"
STAMP=$(date +%Y%m%d-%H%M%S)

[[ -f "$ROOT/CMakeLists.txt" ]] || { print -u2 "Missing StudioForge source: $ROOT"; exit 1; }
[[ -f "$PATCH_FILE" ]] || { print -u2 "Missing trace patch: $PATCH_FILE"; exit 1; }
[[ -f "$CSV_ALIGNMENT_PATCH_FILE" ]] || { print -u2 "Missing CSV alignment patch: $CSV_ALIGNMENT_PATCH_FILE"; exit 1; }

cd "$ROOT"
if grep -q 'pluginSkippedForLatency' Source/AudioEngine/AudioDiagnosticTracer.h +  && grep -q 'selectPluginTraceTarget' Source/AudioEngine/AudioEngine.cpp; then
  print "Generic plug-in trace is already applied."
elif patch -p1 --dry-run --batch < "$PATCH_FILE" >/dev/null; then
  patch -p1 --batch < "$PATCH_FILE"
  print "Applied generic plug-in processing trace."
else
  print -u2 "Trace patch does not match this StudioForge source tree."
  exit 1
fi

if grep -q 'e.outputMask) + ",,,"' Source/AudioEngine/AudioDiagnosticTracer.cpp; then
  print "Trace CSV column alignment is already applied."
elif patch -p1 --dry-run --batch < "$CSV_ALIGNMENT_PATCH_FILE" >/dev/null; then
  patch -p1 --batch < "$CSV_ALIGNMENT_PATCH_FILE"
  print "Applied trace CSV column alignment."
else
  print -u2 "Trace CSV alignment patch does not match this StudioForge source tree."
  exit 1
fi

if [[ ! -f "$BUILD/CMakeCache.txt" ]]; then
  JUCE_SOURCE="$ROOT/build-macos-arm64/_deps/juce-src"
  [[ -d "$JUCE_SOURCE" ]] || { print -u2 "Pinned JUCE checkout is missing: $JUCE_SOURCE"; exit 1; }
  cmake -S "$ROOT" -B "$BUILD" -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
    -DFETCHCONTENT_SOURCE_DIR_JUCE="$JUCE_SOURCE"
fi

cmake --build "$BUILD" --target StudioForgeDAW StudioForgeCoreTests --parallel 8
"$BUILD/StudioForgeCoreTests"
[[ -d "$SOURCE_APP" ]] || { print -u2 "Release app was not produced: $SOURCE_APP"; exit 1; }

osascript -e 'tell application id "com.StudioForge.StudioForgeDAW" to quit' 2>/dev/null || true
# Finder/LaunchServices can retain the old bundle for a moment after a
# code-signed replacement.  Waiting here prevents the harmless -609 launch
# race from being reported as a failed deployment.
sleep 2
mkdir -p "$DEST_DIR"
if [[ -e "$DEST_APP" ]]; then
  mv "$DEST_APP" "$DEST_DIR/StudioForge Live DAW backup trace-$STAMP.app"
fi
ditto --rsrc --extattr --acl "$SOURCE_APP" "$DEST_APP"
codesign --force --deep --sign - "$DEST_APP"
codesign --verify --deep --strict "$DEST_APP"
sleep 1
if ! open -n "$DEST_APP"; then
  print -u2 "LaunchServices could not open the bundle; starting its signed executable directly."
  "$DEST_APP/Contents/MacOS/StudioForge DAW" >/private/tmp/studioforge-generic-plugin-trace-launch.log 2>&1 &
fi

print ""
print "READY: open the target plug-in editor, press Play for 10 seconds, then stop."
print "A CSV will appear in ~/Documents/StudioForge Diagnostics."
print "The selected slot reports: present, bypassed, processed, latency-skipped, pre-FX and post-FX peaks."
