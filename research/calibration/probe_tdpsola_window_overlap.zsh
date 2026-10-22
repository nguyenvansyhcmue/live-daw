#!/bin/zsh
# Diagnostic A/B only: test whether TD-PSOLA's overlap window is long enough
# to realise a selected pitch. It preserves the production default (0.65),
# installs nothing, and uses isolated build directories.
set -euo pipefail

ROOT="/Users/hiimdrdey/autotune"
VIBE_ROOT="${VIBE_ROOT:-/Users/hiimdrdey/code/daw/autotune}"
DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
HEADER="$VIBE_ROOT/VibeAutotune/CausalTDPSOLARenderer.h"
JUCE="$DAW_ROOT/build-macos-arm64/_deps/juce-src"
LINEAR="$VIBE_ROOT/.third_party/signalsmith_linear-src"
STRETCH="$VIBE_ROOT/.third_party/signalsmith_stretch-src"

[[ -f "$HEADER" && -f "$JUCE/CMakeLists.txt" && -f "$LINEAR/CMakeLists.txt" && -f "$STRETCH/CMakeLists.txt" ]] || {
  print -u2 'Missing renderer or pinned dependency source.'; exit 2
}

# A compile-time override seam; default behaviour remains byte-for-byte 0.65.
python3 - "$HEADER" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
old = '    static constexpr double analysisHalfWindowFactor = 0.65;'
new = '''#ifndef VIBE_TDPSOLA_ANALYSIS_HALF_WINDOW_FACTOR
#define VIBE_TDPSOLA_ANALYSIS_HALF_WINDOW_FACTOR 0.65
#endif
    static constexpr double analysisHalfWindowFactor = VIBE_TDPSOLA_ANALYSIS_HALF_WINDOW_FACTOR;'''
if new in text:
    print('TD-PSOLA window override seam already installed; default remains 0.65.')
elif text.count(old) == 1:
    path.write_text(text.replace(old, new, 1))
    print('Installed TD-PSOLA window override seam; default remains 0.65.')
else:
    raise SystemExit('Refusing to edit: analysis-half-window anchor missing or ambiguous.')
PY

common='-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_RAPID_ADJACENT_EVIDENCE_WINDOW_FRAMES=8 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=1024 -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=128'
OUT="$ROOT/artifacts/tdpsola-window-overlap-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"

for factor in 0.65 1.00 1.20; do
  build="/private/tmp/vibe-tdpsola-window-${factor//./_}"
  flags="$common -DVIBE_TDPSOLA_ANALYSIS_HALF_WINDOW_FACTOR=$factor"
  cmake -S "$VIBE_ROOT" -B "$build" -DCMAKE_BUILD_TYPE=Release \
    -DVIBE_JUCE_SOURCE_DIR:PATH="$JUCE" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$LINEAR" \
    -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$STRETCH" \
    -DCMAKE_CXX_FLAGS:STRING="$flags" > "$OUT/window-${factor}.configure.log"
  cmake --build "$build" --target VibeAutotuneKeyScaleLivePathTest --parallel 1 > "$OUT/window-${factor}.build.log"
  set +e
  "$build/VibeAutotuneKeyScaleLivePathTest" > "$OUT/window-${factor}.run.log" 2>&1
  code=$?
  set -e
  print "=== WINDOW $factor (exit $code) ==="
  rg 'key_scale_(autocorrelation_probe|live_probe|synthesis_probe)|FAILED|key_scale_live \|' "$OUT/window-${factor}.run.log" || true
done

print "\nPROBE COMPLETE (not installed): $OUT"
