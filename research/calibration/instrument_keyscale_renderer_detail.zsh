#!/bin/zsh
# Adds per-control-tick detail to the Key/Scale renderer diagnostic fixture.
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
if 'key_scale_renderer_tick | sample=' in text:
    print('Key/Scale renderer tick telemetry already installed.')
    raise SystemExit(0)
anchor = '''              << " output_control_target=" << latestSourceTarget << '\\n';
    const auto outputF0 = estimateF0'''
replacement = '''              << " output_control_target=" << latestSourceTarget << '\\n';
    for (int index = 0; index < diagnosticCount; ++index)
    {
        const auto& frame = diagnosticFrames[static_cast<size_t> (index)];
        std::cout << "key_scale_renderer_tick | sample=" << frame.sampleIndex
                  << " raw_hz=" << frame.rawF0Hz
                  << " stable_hz=" << frame.stableF0Hz
                  << " input_ct=" << frame.inputPitchCents
                  << " target_ct=" << frame.targetPitchCents
                  << " desired_ct=" << frame.desiredCorrectionCents
                  << " requested_ct=" << 1200.0 * std::log2 (frame.requestedRendererRatio)
                  << " delivered_ct=" << frame.deliveredRendererCorrectionCents
                  << " renderer_input_ct=" << frame.rendererInputCorrectionCents
                  << " renderer_post_ct=" << frame.rendererPostGuardCorrectionCents
                  << " source_hz=" << frame.sourceControlF0Hz
                  << " source_target=" << frame.sourceControlTargetMidi
                  << " source_ct=" << 1200.0 * std::log2 (frame.sourceControlPitchRatio)
                  << " wet=" << frame.dryWetMix
                  << " active=" << frame.correctionIsActive << '\\n';
    }
    const auto outputF0 = estimateF0'''
if anchor not in text:
    raise SystemExit('Refusing to edit: renderer summary anchor not found. Run instrument_keyscale_renderer_path.zsh first.')
path.write_text(text.replace(anchor, replacement, 1))
print('Installed per-tick Key/Scale renderer telemetry. DSP behavior unchanged.')
PY
