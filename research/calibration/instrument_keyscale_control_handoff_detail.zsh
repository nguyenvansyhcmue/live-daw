#!/bin/zsh
# Adds source-vs-renderer control lookup provenance to the isolated test.
# Test-only telemetry; no DSP/plug-in installation change.
set -euo pipefail
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
TEST="$VIBE_ROOT/tests/KeyScaleLivePathTest.cpp"
[[ -f "$TEST" ]] || { print -u2 "Missing: $TEST"; exit 2; }

python3 - "$TEST" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
if 'key_scale_control_handoff_probe | caller_time=' in text:
    print('Key/Scale control-handoff telemetry already installed.')
    raise SystemExit(0)
anchor = '''        std::cout << "key_scale_synthesis_probe | expected_period=" << frame.synthExpectedPeriod'''
replacement = '''        std::cout << "key_scale_control_handoff_probe | caller_time=" << frame.callerControlLookupTime
                  << " renderer_time=" << frame.rendererControlLookupTime
                  << " caller_timestamp=" << frame.callerControlTimestamp
                  << " renderer_timestamp=" << frame.rendererControlTimestamp
                  << " caller_ct=" << 1200.0 * std::log2 (frame.callerControlPitchRatio)
                  << " renderer_ct=" << 1200.0 * std::log2 (frame.rendererControlPitchRatio)
                  << " caller_event=" << frame.callerControlEventId
                  << " renderer_event=" << frame.rendererControlEventId << '\\n';
        std::cout << "key_scale_synthesis_probe | expected_period=" << frame.synthExpectedPeriod'''
if anchor not in text:
    raise SystemExit('Refusing to edit: synthesis telemetry anchor missing.')
path.write_text(text.replace(anchor, replacement, 1))
print('Installed Key/Scale control-handoff telemetry. DSP behavior unchanged.')
PY

BUILD_DIR="${VIBE_BUILD_DIR:-$VIBE_ROOT/build-alto-1024-128-qualification}"
cmake --build "$BUILD_DIR" --target VibeAutotuneKeyScaleLivePathTest --parallel 1
"$BUILD_DIR/VibeAutotuneKeyScaleLivePathTest"
