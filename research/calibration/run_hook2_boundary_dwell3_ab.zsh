#!/bin/zsh
# One bounded target-stability candidate. Never installs a plug-in.
set -euo pipefail
root=/Users/hiimdrdey/autotune
vibe=/Users/hiimdrdey/code/daw/autotune
daw=/Users/hiimdrdey/code/daw
raw="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
runner="$daw/build-calibration-arm64/StudioForgeCalibrationRunner"
artist="$root/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
analyser="$daw/Tools/analyze_studioforge_calibration.py"
out="$root/artifacts/hook2-boundary-dwell3-current-$(date +%Y%m%d-%H%M%S)"
# Build products belong in the writable experiment workspace. The canonical
# source tree remains read-only and is never patched by this candidate.
build="$root/build-hook2-boundary-dwell3-current"
for item in "$raw" "$runner" "$artist" "$analyser" "$vibe/.third_party/signalsmith_linear-src/CMakeLists.txt" "$vibe/.third_party/signalsmith_stretch-src/CMakeLists.txt"; do
  [[ -e "$item" ]] || { print -u2 "Missing input: $item"; exit 66; }
done
mkdir -p "$out/vibe"
flags='-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=3 -DVIBE_RAPID_ADJACENT_EVIDENCE_WINDOW_FRAMES=8 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=1024 -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=128 -DVIBE_HARD_LOCK_RENDERER_CROSSING_TRANSITION_MS=24.0'
cmake -S "$vibe" -B "$build" -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release \
  -DVIBE_JUCE_SOURCE_DIR:PATH="$daw/build-macos-arm64/_deps/juce-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$vibe/.third_party/signalsmith_linear-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$vibe/.third_party/signalsmith_stretch-src" \
  -DCMAKE_CXX_FLAGS:STRING="$flags"
cmake --build "$build" --target VibeAutotune_VST3 --parallel 4 | tee "$out/build.log"
candidate="$build/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3"
"$runner" "$raw" "$out/vibe" VibeAutotune "$candidate" | tee "$out/host-runner.log"
awk -F, 'NR == 1 || $1 == 0' "$out/vibe/calibration-report.csv" > "$out/vibe-hardtune-report.csv"
awk -F, 'NR == 1 || $1 == 0' "$artist" > "$out/artist-hardtune-report.csv"
python3 "$analyser" "$raw" "$out/vibe-hardtune-report.csv" "$out/artist-hardtune-report.csv" "$out/comparison"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$root/fit_studioforge_transitions.py" "$raw" "$out/vibe-hardtune-report.csv" "$out/artist-hardtune-report.csv" "$out/transitions" --pitch-tools "$vibe/tools"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$root/analyze_hook2_correction_transfer.py" "$raw" "$out/artist-hardtune-report.csv" "$out/vibe-hardtune-report.csv" "$out/transfer" --pitch-tools "$vibe/tools"
python3 "$root/diagnose_hook2_transition_transfer.py" "$out/transfer/transfer-frame-debug.csv" "$out/transitions/transition-events.csv" "$out/transition-transfer-diagnosis.md"
print "\nCOMPLETE (candidate not installed): $out"
print "Read: $out/comparison/calibration-report.md"
print "Transitions: $out/transition-transfer-diagnosis.md"
