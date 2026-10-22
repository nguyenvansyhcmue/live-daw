#!/bin/zsh
# Makes the Key/Scale renderer fixture deterministic. Every sharp in a Major
# scale lies exactly midway between two legal notes; a real tracker will
# legitimately select either neighbour as its F0 fluctuates by fractions of a
# cent. Bias the synthetic test tone 18 cents toward the lower legal note so
# it validates renderer pitch delivery, not tie-breaking jitter.
# Test-source only: no production DSP, parameters, or plug-in installation.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
TEST="$VIBE_ROOT/tests/KeyScaleLivePathTest.cpp"
[[ -f "$TEST" ]] || { print -u2 "Missing: $TEST"; exit 2; }

python3 - "$TEST" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
old = '    const auto inputHz = midiToHz (inputMidi);'
new = '''    // C#/D#/F#/G#/A# are exact half-way ties in C Major. Keep the
    // synthetic fixture outside the scale, but offset it slightly toward
    // the lower legal neighbour so a sub-cent detector fluctuation cannot
    // turn this renderer-delivery assertion into a selector tie test.
    const auto inputHz = midiToHz (inputMidi) * std::exp2 (-18.0 / 1200.0);'''
if new in text:
    print('Deterministic Key/Scale fixture bias already applied.')
elif text.count(old) == 1:
    path.write_text(text.replace(old, new, 1))
    print('Applied deterministic -18 cents Key/Scale fixture bias.')
else:
    raise SystemExit('Refusing to edit: input tone anchor missing or ambiguous.')
PY

BUILD_DIR="${VIBE_BUILD_DIR:-$VIBE_ROOT/build-alto-1024-128-qualification}"
cmake --build "$BUILD_DIR" --target VibeAutotuneKeyScaleLivePathTest --parallel 1
"$BUILD_DIR/VibeAutotuneKeyScaleLivePathTest"
