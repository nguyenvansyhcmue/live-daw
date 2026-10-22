#!/bin/zsh
# Aligns the regression fixture with the already-promoted Hook-2 Retune law.
# It changes test expectations only; DSP source, plug-in bundles, and installs
# are deliberately untouched.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
TEST="$VIBE_ROOT/tests/CorrectionTrajectoryTest.cpp"
[[ -f "$TEST" ]] || { print -u2 "Missing: $TEST"; exit 2; }

python3 - "$TEST" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
old = '''    require (std::abs (retuneLaw.getEffectiveRetuneTimeMs (10.0) - 23.162) < 0.01,
             "10 ms must use the measured Artist time constant");
    require (std::abs (retuneLaw.getEffectiveRetuneTimeMs (25.0) - 41.686) < 0.01,
             "25 ms must use the measured Artist time constant");
'''
new = '''    // The Hook-2 calibrated control profile uses the verified 20/40 ms T90
    // knots here. Keep this test coupled to that production contract rather
    // than to the older pre-calibration fixture.
    require (std::abs (retuneLaw.getEffectiveRetuneTimeMs (10.0) - (20.0 / 2.302585092994046)) < 0.01,
             "10 ms must use the calibrated Hook-2 Artist time constant");
    require (std::abs (retuneLaw.getEffectiveRetuneTimeMs (25.0) - (40.0 / 2.302585092994046)) < 0.01,
             "25 ms must use the calibrated Hook-2 Artist time constant");
'''
if new in text:
    print('Retune regression contract already matches the calibrated profile.')
elif old in text:
    path.write_text(text.replace(old, new, 1))
    print('Updated Retune regression expectations; DSP source was not changed.')
else:
    raise SystemExit('Refusing to edit: expected old Retune fixture was not found.')
PY
