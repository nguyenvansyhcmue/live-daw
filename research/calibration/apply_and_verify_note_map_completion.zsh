#!/bin/zsh
# Applies the Note Map completion exactly once, proves the source contains it,
# then rebuilds and runs the two deterministic Note Map tests.
set -euo pipefail

PROJECT="${1:-/Users/hiimdrdey/code/daw/autotune}"
PATCH_ROOT="${0:A:h}"
cd "$PROJECT"

if ! rg -q 'VocalTargetRange' VibeAutotune/NotePolicy.h; then
  patch --batch -p1 < "$PATCH_ROOT/vibe-note-map-dsp-completion.patch"
fi

if ! rg -q 'keyParameter->setValueNotifyingHost .*0\.0f' tests/NotePolicyTest.cpp; then
  patch --batch -p1 < "$PATCH_ROOT/vibe-note-policy-test-key-initialisation-fix.patch"
fi

rg -n 'VocalTargetRange|isLegalTarget|range=pass empty=pass' \
  VibeAutotune/NotePolicy.h VibeAutotune/CorrectionTrajectory.h tests/NotePolicyTest.cpp

BUILD="$PROJECT/build-retune-fit"
cmake --build "$BUILD" \
  --target VibeAutotuneNotePolicyTest VibeAutotuneKeyScaleLivePathTest \
  --parallel 8

"$BUILD/VibeAutotuneNotePolicyTest"
"$BUILD/VibeAutotuneKeyScaleLivePathTest"
