#!/bin/zsh
# Adds time-window F0 measurements to the isolated C-major TD-PSOLA test.
# Test-only instrumentation; it leaves processor DSP and installed plug-ins untouched.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
TEST="$VIBE_ROOT/tests/KeyScaleLivePathTest.cpp"
[[ -f "$TEST" ]] || { print -u2 "Missing: $TEST"; exit 2; }

python3 - "$TEST" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
if 'key_scale_output_window | second=' in text:
    print('Key/Scale output-window telemetry already installed.')
    raise SystemExit(0)
anchor = '''    const auto outputF0 = estimateF0 (output, processor.getLatencySamples() + static_cast<int> (sampleRate),
                                      processor.getLatencySamples() + static_cast<int> (sampleRate * 2.0));'''
replacement = '''    for (int second = 0; second < 3; ++second)
    {
        const auto startSample = processor.getLatencySamples() + static_cast<int> (sampleRate * second);
        const auto endSample = std::min (static_cast<int> (output.size()), startSample + static_cast<int> (sampleRate));
        if (endSample - startSample > 4096)
            std::cout << "key_scale_output_window | second=" << second
                      << " hz=" << estimateF0 (output, startSample, endSample) << '\\n';
    }
    const auto outputF0 = estimateF0 (output, processor.getLatencySamples() + static_cast<int> (sampleRate),
                                      processor.getLatencySamples() + static_cast<int> (sampleRate * 2.0));'''
if anchor not in text:
    raise SystemExit('Refusing to edit: output F0 anchor missing.')
path.write_text(text.replace(anchor, replacement, 1))
print('Installed Key/Scale output-window telemetry. DSP behavior unchanged.')
PY
