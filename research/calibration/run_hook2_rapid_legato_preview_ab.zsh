#!/bin/zsh
# Isolated A/B for the existing bounded rapid-legato preview. Never installs.
set -euo pipefail
root=/Users/hiimdrdey/autotune
source_root=/Users/hiimdrdey/code/daw/autotune
daw=/Users/hiimdrdey/code/daw
raw="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
artist="$root/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
runner="$daw/build-calibration-arm64/StudioForgeCalibrationRunner"
analyser="$daw/Tools/analyze_studioforge_calibration.py"
stamp=$(date +%Y%m%d-%H%M%S)
out="$root/artifacts/hook2-rapid-legato-preview-current-$stamp"
candidate="$out/source"
build="$root/build-hook2-rapid-legato-preview-current"
for item in "$raw" "$artist" "$runner" "$analyser" "$source_root/CMakeLists.txt" "$source_root/.third_party"; do
  [[ -e "$item" ]] || { print -u2 "Missing input: $item"; exit 66; }
done
mkdir -p "$candidate"
rsync -a --exclude='.git' --exclude='build*' --exclude='.third_party' --exclude='artifacts' --exclude='renders' --exclude='artist-renders' --exclude='benchmark' --exclude='data' --exclude='JUCE' --exclude='JUCE_SDK' "$source_root/" "$candidate/"
ln -s "$source_root/.third_party" "$candidate/.third_party"
python3 - "$candidate/VibeAutotune/PluginProcessor.cpp" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); text=p.read_text()
old='correctionTrajectory.setDiagnosticRapidLegatoPreview (false);'
if text.count(old) != 1: raise SystemExit('Preview anchor missing/ambiguous; candidate abandoned.')
p.write_text(text.replace(old, 'correctionTrajectory.setDiagnosticRapidLegatoPreview (true);', 1))
PY
shasum -a 256 "$source_root/VibeAutotune/PluginProcessor.cpp" "$candidate/VibeAutotune/PluginProcessor.cpp" > "$out/source-sha256.txt"
flags='-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_RAPID_ADJACENT_EVIDENCE_WINDOW_FRAMES=8 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=1024 -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=128 -DVIBE_HARD_LOCK_RENDERER_CROSSING_TRANSITION_MS=24.0'
cmake -S "$candidate" -B "$build" -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release -DVIBE_JUCE_SOURCE_DIR:PATH="$daw/build-macos-arm64/_deps/juce-src" -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$candidate/.third_party/signalsmith_linear-src" -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$candidate/.third_party/signalsmith_stretch-src" -DCMAKE_CXX_FLAGS:STRING="$flags"
cmake --build "$build" --target VibeAutotune_VST3 --parallel 4 | tee "$out/build.log"
plugin="$build/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
mkdir -p "$out/vibe"
"$runner" "$raw" "$out/vibe" VibeAutotune "$plugin" | tee "$out/host-runner.log"
awk -F, 'NR == 1 || $1 == 0' "$out/vibe/calibration-report.csv" > "$out/vibe-hardtune-report.csv"
awk -F, 'NR == 1 || $1 == 0' "$artist" > "$out/artist-hardtune-report.csv"
python3 "$analyser" "$raw" "$out/vibe-hardtune-report.csv" "$out/artist-hardtune-report.csv" "$out/comparison"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$root/fit_studioforge_transitions.py" "$raw" "$out/vibe-hardtune-report.csv" "$out/artist-hardtune-report.csv" "$out/transitions" --pitch-tools "$candidate/tools"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$root/analyze_hook2_correction_transfer.py" "$raw" "$out/artist-hardtune-report.csv" "$out/vibe-hardtune-report.csv" "$out/transfer" --pitch-tools "$candidate/tools"
python3 "$root/diagnose_hook2_transition_transfer.py" "$out/transfer/transfer-frame-debug.csv" "$out/transitions/transition-events.csv" "$out/transition-transfer-diagnosis.md"
print "\nCOMPLETE (preview candidate not installed): $out"
