#!/bin/zsh
# Updates the conformance test to the current private control-ring API.
# No DSP, plug-in bundle, or installation is changed.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
TEST="$VIBE_ROOT/tests/ControlHandoffTest.cpp"
[[ -f "$TEST" ]] || { print -u2 "Missing: $TEST"; exit 2; }

python3 - "$TEST" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
replacements = {
    'return processor.getSignalsmithControlFrame (timestamp);':
        'return processor.getRendererControlFrame (timestamp);',
    'processor.pushPsolaControlFrame (timestamp, f0, ratio, valid);':
        'processor.pushPsolaControlFrame (timestamp, f0, ratio, 0.0, valid);',
}
changed = False
for old, new in replacements.items():
    if new in text:
        continue
    if old not in text:
        raise SystemExit(f'Refusing to edit: expected stale API call not found: {old}')
    text = text.replace(old, new, 1)
    changed = True
if changed:
    path.write_text(text)
    print('Updated ControlHandoffTest for the current renderer-control ring API.')
else:
    print('ControlHandoffTest already uses the current renderer-control ring API.')
PY
