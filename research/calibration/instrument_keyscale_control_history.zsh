#!/bin/zsh
# Dumps the exact materialised PSOLA controls around the audible wrong grain.
# Test-only telemetry; no DSP or plug-in installation changes.
set -euo pipefail
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
TEST="$VIBE_ROOT/tests/KeyScaleLivePathTest.cpp"
[[ -f "$TEST" ]] || { print -u2 "Missing: $TEST"; exit 2; }

python3 - "$TEST" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
if 'key_scale_control_history | sequence=' in text:
    print('Key/Scale control-history telemetry already installed.')
    raise SystemExit(0)
anchor = '''    std::cout << "key_scale_renderer_probe | frames=" << diagnosticCount'''
replacement = '''    std::array<VibeAutotuneProcessor::ControlMaterializationEvent, 4096> controlEvents {};
    const auto controlEventCount = processor.copyControlMaterializationEvents (
        controlEvents.data(), static_cast<int> (controlEvents.size()));
    for (int index = 0; index < controlEventCount; ++index)
    {
        const auto& event = controlEvents[static_cast<size_t> (index)];
        if (event.timestampSamples < 141000 || event.timestampSamples > 144000)
            continue;
        std::cout << "key_scale_control_history | sequence=" << event.sequence
                  << " timestamp=" << event.timestampSamples
                  << " target_event=" << event.targetEventId
                  << " scheduled_ct=" << event.scheduledCorrectionCents
                  << " after_ct=" << event.correctionAfterAdvance
                  << " transition_target=" << event.transitionTargetCents
                  << " progress=" << event.transitionProgress << '\\n';
    }
    std::cout << "key_scale_renderer_probe | frames=" << diagnosticCount'''
if anchor not in text:
    raise SystemExit('Refusing to edit: renderer probe anchor missing.')
path.write_text(text.replace(anchor, replacement, 1))
print('Installed Key/Scale control-history telemetry. DSP behavior unchanged.')
PY

BUILD_DIR="${VIBE_BUILD_DIR:-$VIBE_ROOT/build-alto-1024-128-qualification}"
cmake --build "$BUILD_DIR" --target VibeAutotuneKeyScaleLivePathTest --parallel 1
"$BUILD_DIR/VibeAutotuneKeyScaleLivePathTest"
