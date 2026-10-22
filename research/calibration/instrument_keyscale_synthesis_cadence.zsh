#!/bin/zsh
# Extends the isolated C-major fixture with TD-PSOLA synthesis-cadence facts.
# Test-only edit; this does not change plug-in DSP or install anything.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
TEST="$VIBE_ROOT/tests/KeyScaleLivePathTest.cpp"
[[ -f "$TEST" ]] || { print -u2 "Missing: $TEST"; exit 2; }

python3 - "$TEST" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
if 'key_scale_synthesis_probe | expected_period=' in text:
    print('Key/Scale synthesis-cadence telemetry already installed.')
    raise SystemExit(0)
anchor = '''        std::cout << "key_scale_grain_probe | weight=" << frame.olaOverlapWeight'''
replacement = '''        std::cout << "key_scale_synthesis_probe | expected_period=" << frame.synthExpectedPeriod
                  << " actual_period=" << frame.synthActualPeriod
                  << " period_error=" << frame.synthPeriodError
                  << " source_spacing=" << frame.synthSourceSpacing
                  << " expected_hz=" << (frame.synthExpectedPeriod > 0.0 ? 48000.0 / frame.synthExpectedPeriod : 0.0)
                  << " actual_hz=" << (frame.synthActualPeriod > 0.0 ? 48000.0 / frame.synthActualPeriod : 0.0) << '\\n';
        std::cout << "key_scale_grain_probe | weight=" << frame.olaOverlapWeight'''
if anchor not in text:
    raise SystemExit('Refusing to edit: grain telemetry anchor missing. Run instrument_keyscale_renderer_grain_state.zsh first.')
path.write_text(text.replace(anchor, replacement, 1))
print('Installed Key/Scale synthesis-cadence telemetry. DSP behavior unchanged.')
PY
