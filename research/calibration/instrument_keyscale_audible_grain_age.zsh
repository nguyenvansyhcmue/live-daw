#!/bin/zsh
# Reveals exactly which TD-PSOLA grain is audible at the failed output sample.
# Test-only telemetry; no renderer behavior or installation changes.
set -euo pipefail
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
TEST="$VIBE_ROOT/tests/KeyScaleLivePathTest.cpp"
[[ -f "$TEST" ]] || { print -u2 "Missing: $TEST"; exit 2; }

python3 - "$TEST" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
if 'key_scale_audible_grain_probe | dominant_epoch=' in text:
    print('Key/Scale audible-grain telemetry already installed.')
    raise SystemExit(0)
anchor = '''        std::cout << "key_scale_grain_probe | weight=" << frame.olaOverlapWeight'''
replacement = '''        std::cout << "key_scale_audible_grain_probe | dominant_epoch=" << frame.olaDominantGrainEpoch
                  << " source_mark=" << frame.olaSourceMarkTime
                  << " source_hz=" << frame.olaSourceMarkF0
                  << " grain_age=" << frame.olaAudibleGrainAge
                  << " target_event=" << frame.olaDominantGrainTargetEventId
                  << " control_event=" << frame.olaDominantGrainControlEventId
                  << " target_timestamp=" << frame.olaDominantGrainTargetControlTimestamp
                  << " candidate_weight=" << frame.olaTargetCandidateWeight
                  << " candidate_epoch=" << frame.olaTargetCandidateEpoch
                  << " candidate_hz=" << frame.olaTargetCandidateExpectedF0 << '\\n';
        std::cout << "key_scale_grain_probe | weight=" << frame.olaOverlapWeight'''
if anchor not in text:
    raise SystemExit('Refusing to edit: grain probe anchor missing.')
path.write_text(text.replace(anchor, replacement, 1))
print('Installed Key/Scale audible-grain telemetry. DSP behavior unchanged.')
PY

BUILD_DIR="${VIBE_BUILD_DIR:-$VIBE_ROOT/build-alto-1024-128-qualification}"
cmake --build "$BUILD_DIR" --target VibeAutotuneKeyScaleLivePathTest --parallel 1
"$BUILD_DIR/VibeAutotuneKeyScaleLivePathTest"
