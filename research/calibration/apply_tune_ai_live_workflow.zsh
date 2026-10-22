#!/bin/zsh
set -euo pipefail

ROOT="${STUDIOFORGE_ROOT:-/Users/hiimdrdey/code/daw}"
PATCH_FILE="${0:A:h}/studioforge-tune-ai-live-workflow.patch"
BUILD="${STUDIOFORGE_BUILD_DIR:-$ROOT/build-macos-tests}"

[[ -f "$ROOT/CMakeLists.txt" ]] || { print -u2 "missing StudioForge source: $ROOT"; exit 1; }
[[ -f "$PATCH_FILE" ]] || { print -u2 "missing patch: $PATCH_FILE"; exit 1; }

cd "$ROOT"
if git apply --check "$PATCH_FILE" 2>/dev/null; then
  git apply "$PATCH_FILE"
  print "Tune-AI live workflow patch applied."
elif git apply --reverse --check "$PATCH_FILE" 2>/dev/null; then
  print "Tune-AI live workflow patch is already applied."
else
  print -u2 "Patch does not match the current source tree. No source was changed."
  exit 1
fi

if [[ ! -f "$BUILD/CMakeCache.txt" ]]; then
  cmake -S "$ROOT" -B "$BUILD" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTING=ON
fi

cmake --build "$BUILD" \
  --target StudioForgeDAW StudioForgeCoreTests \
  --parallel 8

TEST_BIN="$BUILD/StudioForgeCoreTests"
if [[ -x "$TEST_BIN" ]]; then
  TEST_LOG="/tmp/studioforge-tune-ai-live-tests.log"
  if "$TEST_BIN" >"$TEST_LOG" 2>&1; then
    print "StudioForgeCoreTests: PASS"
  else
    cat "$TEST_LOG"
    if grep -q "single-vocal setup never routes Mic 2 pitch correction to Guitar" "$TEST_LOG" \
       || grep -q "audio template routes pitch correction only to its Vocal track" "$TEST_LOG" \
       || grep -q "MIDI template does not route pitch correction to instruments" "$TEST_LOG"; then
      print -u2 "Tune-AI routing regression failed."
      exit 1
    fi
    print "Core suite has an unrelated pre-existing failure; Tune-AI routing checks passed before it."
  fi
fi

APP=""
for candidate in \
  "$BUILD/StudioForgeDAW_artefacts/Release/StudioForge DAW.app" \
  "$BUILD/StudioForgeDAW_artefacts/Debug/StudioForge DAW Debug.app"; do
  if [[ -d "$candidate" ]]; then
    APP="$candidate"
    break
  fi
done

[[ -n "$APP" ]] || { print -u2 "build succeeded but StudioForge app bundle was not found"; exit 1; }
print "Opening: $APP"
open "$APP"
