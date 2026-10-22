#!/bin/zsh
# Extends the Key/Scale integration fixture with production-path renderer
# telemetry. Test-only source edit; no DSP or bundle installation changes.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
TEST="$VIBE_ROOT/tests/KeyScaleLivePathTest.cpp"
[[ -f "$TEST" ]] || { print -u2 "Missing: $TEST"; exit 2; }

python3 - "$TEST" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
if 'key_scale_renderer_probe | frames=' in text:
    print('Key/Scale renderer-path telemetry already installed.')
    raise SystemExit(0)

if '#include <algorithm>\n' not in text:
    include_anchor = '#include "PluginProcessor.h"\n'
    if include_anchor not in text:
        raise SystemExit('Refusing to edit: include anchor not found.')
    text = text.replace(include_anchor, include_anchor + '\n#include <algorithm>\n', 1)

anchor = '''    VibeAutotuneProcessor processor;
    processor.prepareToPlay (sampleRate, blockSize);
'''
replacement = '''    VibeAutotuneProcessor processor;
    processor.prepareToPlay (sampleRate, blockSize);
    processor.setSignalChainDiagnosticEnabled (true);
'''
if anchor not in text:
    raise SystemExit('Refusing to edit: prepare anchor not found.')
text = text.replace(anchor, replacement, 1)
anchor = '''    require (sawLegalTarget, "C Major live path did not acquire a target");
    const auto outputF0 = estimateF0 (output, processor.getLatencySamples() + static_cast<int> (sampleRate),
'''
replacement = '''    require (sawLegalTarget, "C Major live path did not acquire a target");
    std::array<VibeAutotuneProcessor::SignalChainDiagnosticFrame, 4096> diagnosticFrames {};
    const auto diagnosticCount = processor.copySignalChainDiagnosticFrames (
        diagnosticFrames.data(), static_cast<int> (diagnosticFrames.size()));
    auto activeFrames = 0;
    auto maxMix = 0.0f;
    auto latestRequestedCents = 0.0;
    auto latestDeliveredCents = 0.0f;
    auto latestSourceTarget = -1;
    for (int index = 0; index < diagnosticCount; ++index)
    {
        const auto& frame = diagnosticFrames[static_cast<size_t> (index)];
        activeFrames += frame.correctionIsActive ? 1 : 0;
        maxMix = std::max (maxMix, frame.dryWetMix);
        latestRequestedCents = 1200.0 * std::log2 (frame.requestedRendererRatio);
        latestDeliveredCents = frame.deliveredRendererCorrectionCents;
        latestSourceTarget = frame.outputRendererControlTargetMidi;
    }
    std::cout << "key_scale_renderer_probe | frames=" << diagnosticCount
              << " active=" << activeFrames
              << " max_wet=" << maxMix
              << " requested_ct=" << latestRequestedCents
              << " delivered_ct=" << latestDeliveredCents
              << " output_control_target=" << latestSourceTarget << '\\n';
    const auto outputF0 = estimateF0 (output, processor.getLatencySamples() + static_cast<int> (sampleRate),
'''
if anchor not in text:
    raise SystemExit('Refusing to edit: output-measurement anchor not found.')
path.write_text(text.replace(anchor, replacement, 1))
print('Installed Key/Scale renderer-path telemetry. DSP behavior unchanged.')
PY
