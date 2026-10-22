#!/bin/zsh
# Adds an independent autocorrelation F0 estimator to the C-major fixture.
# Test-only telemetry; it does not change plug-in DSP or installation state.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
TEST="$VIBE_ROOT/tests/KeyScaleLivePathTest.cpp"
[[ -f "$TEST" ]] || { print -u2 "Missing: $TEST"; exit 2; }

python3 - "$TEST" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
if 'estimateAutocorrelationF0' in text:
    print('Key/Scale autocorrelation telemetry already installed.')
    raise SystemExit(0)

marker = '\nbool isCMajor (int midi) noexcept\n'
function = r'''
double estimateAutocorrelationF0 (const std::vector<float>& samples, int start, int end)
{
    start = std::max (0, start);
    end = std::min (static_cast<int> (samples.size()), end);
    constexpr int minimumLag = 128, maximumLag = 300;
    if (end - start <= maximumLag + 1024)
        return std::numeric_limits<double>::quiet_NaN();
    auto bestLag = -1;
    auto bestScore = -std::numeric_limits<double>::infinity();
    for (int lag = minimumLag; lag <= maximumLag; ++lag)
    {
        double dot = 0.0, leftEnergy = 0.0, rightEnergy = 0.0;
        for (int sample = start + lag; sample < end; ++sample)
        {
            const auto left = static_cast<double> (samples[static_cast<size_t> (sample)]);
            const auto right = static_cast<double> (samples[static_cast<size_t> (sample - lag)]);
            dot += left * right;
            leftEnergy += left * left;
            rightEnergy += right * right;
        }
        const auto score = dot / std::sqrt (leftEnergy * rightEnergy + 1.0e-18);
        if (score > bestScore) { bestScore = score; bestLag = lag; }
    }
    return bestLag > 0 ? sampleRate / static_cast<double> (bestLag)
                       : std::numeric_limits<double>::quiet_NaN();
}
'''
if marker not in text:
    raise SystemExit('Refusing to edit: estimator insertion marker missing.')
text = text.replace(marker, '\n' + function + marker, 1)
anchor = '    const auto outputMidi = static_cast<int> (std::lround (69.0 + 12.0 * std::log2 (outputF0 / 440.0)));'
replacement = '''    const auto outputAutocorrelationF0 = estimateAutocorrelationF0 (
        output, processor.getLatencySamples() + static_cast<int> (sampleRate),
        processor.getLatencySamples() + static_cast<int> (sampleRate * 2.0));
    std::cout << "key_scale_autocorrelation_probe | zero_cross_hz=" << outputF0
              << " autocorrelation_hz=" << outputAutocorrelationF0 << '\\n';
''' + anchor
if anchor not in text:
    raise SystemExit('Refusing to edit: output MIDI anchor missing.')
path.write_text(text.replace(anchor, replacement, 1))
print('Installed Key/Scale autocorrelation F0 telemetry. DSP behavior unchanged.')
PY

BUILD_DIR="${VIBE_BUILD_DIR:-$VIBE_ROOT/build-alto-1024-128-qualification}"
cmake --build "$BUILD_DIR" --target VibeAutotuneKeyScaleLivePathTest --parallel 1
"$BUILD_DIR/VibeAutotuneKeyScaleLivePathTest"
