#!/bin/zsh
# Extends the Key/Scale fixture with the audible TD-PSOLA grain state.
# Test-only source edit; no DSP or installation changes.
set -euo pipefail

VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
TEST="$VIBE_ROOT/tests/KeyScaleLivePathTest.cpp"
[[ -f "$TEST" ]] || { print -u2 "Missing: $TEST"; exit 2; }

python3 - "$TEST" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
if 'key_scale_grain_probe | weight=' in text:
    print('Key/Scale grain-state telemetry already installed.')
    raise SystemExit(0)
anchor = '''    for (int index = 0; index < diagnosticCount; ++index)
    {
        const auto& frame = diagnosticFrames[static_cast<size_t> (index)];
        std::cout << "key_scale_renderer_tick | sample="'''
replacement = '''    if (diagnosticCount > 0)
    {
        const auto& frame = diagnosticFrames[static_cast<size_t> (diagnosticCount - 1)];
        std::cout << "key_scale_grain_probe | weight=" << frame.olaOverlapWeight
                  << " grain_starved=" << frame.rendererGrainStarved
                  << " should_wet=" << frame.rendererShouldRenderWet
                  << " audible_ratio=" << frame.olaAudibleRatioAtStart
                  << " dominant_ratio=" << frame.olaDominantGrainRatio
                  << " audible_expected_hz=" << frame.olaExpectedGrainF0
                  << " dominant_expected_hz=" << frame.olaDominantGrainExpectedF0
                  << " dominant_target=" << frame.olaDominantGrainTargetMidi
                  << " spawn_ratio=" << frame.ratioAtSpawn
                  << " spawn_expected_hz=" << frame.spawnExpectedF0
                  << " spawn_target=" << frame.spawnTargetMidi << '\\n';
    }
    for (int index = 0; index < diagnosticCount; ++index)
    {
        const auto& frame = diagnosticFrames[static_cast<size_t> (index)];
        std::cout << "key_scale_renderer_tick | sample="'''
if anchor not in text:
    raise SystemExit('Refusing to edit: per-tick telemetry anchor not found. Run instrument_keyscale_renderer_detail.zsh first.')
path.write_text(text.replace(anchor, replacement, 1))
print('Installed Key/Scale grain-state telemetry. DSP behavior unchanged.')
PY
