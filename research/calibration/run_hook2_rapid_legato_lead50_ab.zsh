#!/bin/zsh
# One follow-up only: broaden preview lead from 0.30 to 0.50 semitone in an
# already isolated candidate. No canonical source or installed bundle changes.
set -euo pipefail
root=/Users/hiimdrdey/autotune
base="$root/artifacts/hook2-rapid-legato-preview-current-20261017-121457/source"
daw=/Users/hiimdrdey/code/daw
raw="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
artist="$root/artifacts/hook2-artist-vibe-20261014-041857/artist/calibration-report.csv"
out="$root/artifacts/hook2-rapid-legato-lead50-current-$(date +%Y%m%d-%H%M%S)"
source="$out/source"; build="$root/build-hook2-rapid-legato-lead50-current"
mkdir -p "$out"
rsync -a --exclude='build*' "$base/" "$source/"
python3 - "$source/VibeAutotune/CorrectionTrajectory.h" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
old='diagnosticRapidLegatoPreview ? 0.30 : 0.04'
if s.count(old)!=1: raise SystemExit('Preview-lead anchor missing/ambiguous; candidate abandoned.')
p.write_text(s.replace(old, 'diagnosticRapidLegatoPreview ? 0.50 : 0.04', 1))
PY
flags='-DVIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1 -DVIBE_HARD_LOCK_MAXIMUM_LIVE_CORRECTION_CENTS=160 -DVIBE_HARD_TUNE_TRAJECTORY_PREVIEW=1 -DVIBE_RAPID_ADJACENT_ENTRY_BEYOND_MIDPOINT_CENTS=4 -DVIBE_RAPID_ADJACENT_MINIMUM_DWELL_SAMPLES=3840 -DVIBE_RAPID_ADJACENT_BOUNDARY_DWELL_FRAMES=2 -DVIBE_RAPID_ADJACENT_EVIDENCE_WINDOW_FRAMES=8 -DVIBE_ALTO_ANALYSIS_FRAME_SAMPLES=1024 -DVIBE_ALTO_ANALYSIS_HOP_SAMPLES=128 -DVIBE_HARD_LOCK_RENDERER_CROSSING_TRANSITION_MS=24.0'
cmake -S "$source" -B "$build" -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release -DVIBE_JUCE_SOURCE_DIR:PATH="$daw/build-macos-arm64/_deps/juce-src" -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR:PATH="$source/.third_party/signalsmith_linear-src" -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH:PATH="$source/.third_party/signalsmith_stretch-src" -DCMAKE_CXX_FLAGS:STRING="$flags"
cmake --build "$build" --target VibeAutotune_VST3 --parallel 4 | tee "$out/build.log"
mkdir -p "$out/vibe"; "$daw/build-calibration-arm64/StudioForgeCalibrationRunner" "$raw" "$out/vibe" VibeAutotune "$build/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3" | tee "$out/host-runner.log"
awk -F, 'NR==1 || $1==0' "$out/vibe/calibration-report.csv" > "$out/vibe-hardtune-report.csv"; awk -F, 'NR==1 || $1==0' "$artist" > "$out/artist-hardtune-report.csv"
python3 "$daw/Tools/analyze_studioforge_calibration.py" "$raw" "$out/vibe-hardtune-report.csv" "$out/artist-hardtune-report.csv" "$out/comparison"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$root/fit_studioforge_transitions.py" "$raw" "$out/vibe-hardtune-report.csv" "$out/artist-hardtune-report.csv" "$out/transitions" --pitch-tools "$source/tools"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$root/analyze_hook2_correction_transfer.py" "$raw" "$out/artist-hardtune-report.csv" "$out/vibe-hardtune-report.csv" "$out/transfer" --pitch-tools "$source/tools"
print "COMPLETE (not installed): $out"
