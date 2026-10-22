#!/bin/zsh
# Adds one diagnostic line to the Key/Scale integration test before its
# existing assertion. It changes no DSP or release bundle.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
TEST="$VIBE_ROOT/tests/KeyScaleLivePathTest.cpp"
[[ -f "$TEST" ]] || { print -u2 "Missing: $TEST"; exit 2; }

python3 - "$TEST" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
if 'key_scale_live_probe | input=' in text:
    print('Key/Scale test telemetry already installed.')
    raise SystemExit(0)

anchor = '''    auto sawLegalTarget = false;

    for (int start = 0; start < totalSamples; start += blockSize)
'''
replacement = '''    auto sawLegalTarget = false;
    auto latestTarget = -1;

    for (int start = 0; start < totalSamples; start += blockSize)
'''
if anchor not in text:
    raise SystemExit('Refusing to edit: target-tracking anchor not found.')
text = text.replace(anchor, replacement, 1)
anchor = '''        if (target >= 0)
        {
            require (isCMajor (target), "C Major live target contained an illegal pitch class");
            sawLegalTarget = true;
        }
'''
replacement = '''        if (target >= 0)
        {
            latestTarget = target;
            require (isCMajor (target), "C Major live target contained an illegal pitch class");
            sawLegalTarget = true;
        }
'''
if anchor not in text:
    raise SystemExit('Refusing to edit: target assertion anchor not found.')
text = text.replace(anchor, replacement, 1)
anchor = '''    const auto outputMidi = static_cast<int> (std::lround (69.0 + 12.0 * std::log2 (outputF0 / 440.0)));
    require (std::isfinite (outputF0) && isCMajor (outputMidi), "C Major renderer output remained outside the selected scale");
'''
replacement = '''    const auto outputMidi = static_cast<int> (std::lround (69.0 + 12.0 * std::log2 (outputF0 / 440.0)));
    std::cout << "key_scale_live_probe | input=" << inputMidi
              << " target=" << latestTarget
              << " output_hz=" << outputF0
              << " output=" << outputMidi
              << " latency_samples=" << processor.getLatencySamples() << '\\n';
    require (std::isfinite (outputF0) && isCMajor (outputMidi), "C Major renderer output remained outside the selected scale");
'''
if anchor not in text:
    raise SystemExit('Refusing to edit: renderer assertion anchor not found.')
path.write_text(text.replace(anchor, replacement, 1))
print('Installed Key/Scale test telemetry. DSP behavior unchanged.')
PY
