#!/bin/zsh
# Adds diagnostics only. It does not change audio processing or plug-in defaults.
set -euo pipefail
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
HEADER="$VIBE_ROOT/VibeAutotune/PluginProcessor.h"
SOURCE="$VIBE_ROOT/VibeAutotune/PluginProcessor.cpp"
DIAGNOSTIC="$VIBE_ROOT/tests/SignalChainDiagnostic.cpp"
for f in "$HEADER" "$SOURCE" "$DIAGNOSTIC"; do [[ -f "$f" ]] || { print -u2 "Missing: $f"; exit 2; }; done

python3 - "$HEADER" "$SOURCE" "$DIAGNOSTIC" <<'PY'
from pathlib import Path
import sys
h, c, d = map(Path, sys.argv[1:])
hs, cs, ds = h.read_text(), c.read_text(), d.read_text()
marker = 'outputRendererControlTimestamp'
# Repair the only possible partial insertion from an earlier telemetry script
# revision. It is a CSV stream token typo, never DSP code.
bad_stream_token = "<< f.sourceControlPitchRatio << ','" + "'"
good_stream_token = "<< f.sourceControlPitchRatio << ','"
if bad_stream_token in ds:
    ds = ds.replace(bad_stream_token, good_stream_token)
    d.write_text(ds)
if marker not in hs:
    anchor = '''        uint64_t sourceControlTimestamp = 0;
        double sourceControlF0Hz = std::numeric_limits<double>::quiet_NaN();'''
    repl = '''        uint64_t sourceControlTimestamp = 0;
        // The latency-delayed control used by the output-stage ratio path.
        // Keep it separate from sourceControl*, which belongs to TD-PSOLA.
        uint64_t outputRendererControlTimestamp = 0;
        double outputRendererControlPitchRatio = 1.0;
        int outputRendererControlTargetMidi = -1;
        double sourceControlF0Hz = std::numeric_limits<double>::quiet_NaN();'''
    if hs.count(anchor) != 1: raise SystemExit('Header anchor not unique; no files changed.')
    hs = hs.replace(anchor, repl)
    c_anchor = '''            frame.sourceControlTimestamp = inputRendererControl.timestampSamples;
            frame.sourceControlF0Hz = inputRendererControl.stableF0Hz;'''
    c_repl = '''            frame.sourceControlTimestamp = inputRendererControl.timestampSamples;
            frame.outputRendererControlTimestamp = rendererControl.timestampSamples;
            frame.outputRendererControlPitchRatio = rendererControl.pitchRatio;
            frame.outputRendererControlTargetMidi = rendererControl.targetMidi;
            frame.sourceControlF0Hz = inputRendererControl.stableF0Hz;'''
    if cs.count(c_anchor) != 1: raise SystemExit('Processor anchor not unique; no files changed.')
    cs = cs.replace(c_anchor, c_repl)
    d_anchor = '''        << f.sourceControlTimestamp << ',' << f.sourceControlF0Hz << ',' << f.sourceControlTargetCents << ','
        << f.sourceControlTargetMidi << ',' << f.sourceControlValid << ',' << f.sourceControlHoldDry << ',' << f.sourceControlPitchRatio << ','''
    d_repl = """        << f.sourceControlTimestamp << ',' << f.outputRendererControlTimestamp << ','
        << f.outputRendererControlPitchRatio << ',' << f.outputRendererControlTargetMidi << ','
        << f.sourceControlF0Hz << ',' << f.sourceControlTargetCents << ','
        << f.sourceControlTargetMidi << ',' << f.sourceControlValid << ',' << f.sourceControlHoldDry << ',' << f.sourceControlPitchRatio << ','"""
    if ds.count(d_anchor) != 1: raise SystemExit('CSV writer anchor not unique; no files changed.')
    ds = ds.replace(d_anchor, d_repl)
    header_anchor = 'sourceControlTimestamp,sourceControlF0Hz,sourceControlTargetCents,sourceControlTargetMidi,sourceControlValid,sourceControlHoldDry,sourceControlPitchRatio,'
    header_repl = 'sourceControlTimestamp,outputRendererControlTimestamp,outputRendererControlPitchRatio,outputRendererControlTargetMidi,sourceControlF0Hz,sourceControlTargetCents,sourceControlTargetMidi,sourceControlValid,sourceControlHoldDry,sourceControlPitchRatio,'
    if ds.count(header_anchor) != 1: raise SystemExit('CSV header anchor not unique; no files changed.')
    ds = ds.replace(header_anchor, header_repl)
    h.write_text(hs); c.write_text(cs); d.write_text(ds)
PY

rg -q 'outputRendererControlTimestamp' "$HEADER"
print 'Installed output-renderer control telemetry. DSP behavior unchanged.'
