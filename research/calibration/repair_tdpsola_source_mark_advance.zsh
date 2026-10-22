#!/bin/zsh
# Correct TD-PSOLA source-mark progression: source and synthesis cadences have
# different roles.  This is a targeted DSP fix; no plug-in is installed here.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
RENDERER="$VIBE_ROOT/VibeAutotune/CausalTDPSOLARenderer.h"
BUILD_DIR="${VIBE_BUILD_DIR:-$VIBE_ROOT/build-alto-1024-128-qualification}"
[[ -f "$RENDERER" ]] || { print -u2 "Missing: $RENDERER"; exit 2; }

python3 - "$RENDERER" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
new = '''                    // TD-PSOLA changes pitch by moving synthesis marks.
                    // Consecutive source grains must remain one source period
                    // apart: advancing them by sourcePeriod / ratio makes the
                    // source phase track the output lattice and mathematically
                    // cancels the pitch shift (e.g. C# remains C# despite a
                    // correct C target).  Ratio remains immutable grain
                    // provenance; it does not own source-mark spacing.
                    sourceMarkCursor += safeMark.period;'''
old = '                    sourceMarkCursor += safeMark.period / ratioAtGrainStart;'
if new in text:
    print('TD-PSOLA source-mark cadence fix already applied.')
elif text.count(old) == 1:
    path.write_text(text.replace(old, new, 1))
    print('Applied TD-PSOLA source-mark cadence fix.')
else:
    raise SystemExit('Refusing to edit: expected source-mark advance anchor is missing or ambiguous.')
PY

cmake --build "$BUILD_DIR" --target VibeAutotuneKeyScaleLivePathTest --parallel 1
"$BUILD_DIR/VibeAutotuneKeyScaleLivePathTest"

print 'PASS: TD-PSOLA corrected the full C-major illegal-note fixture.'
print 'Not installed. Run the Hook-2 Artist A/B qualification before promotion.'
