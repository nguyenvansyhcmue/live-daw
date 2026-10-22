#!/bin/zsh
# Isolated diagnostic experiment: never changes source or installed plug-in.
set -euo pipefail
root=/Users/hiimdrdey/autotune
source_root=/Users/hiimdrdey/code/daw/autotune
out="$root/artifacts/crossing24-bounded-preview-$(date +%Y%m%d-%H%M%S)"
candidate="$out/source"
[[ -f "$source_root/CMakeLists.txt" && -d "$source_root/.third_party" ]] || {
  print -u2 'Missing source or dependencies'; exit 1
}
mkdir -p "$candidate"
rsync -a --exclude='.git' --exclude='build*' --exclude='.third_party' \
  --exclude='artifacts' --exclude='renders' --exclude='artist-renders' \
  --exclude='benchmark' --exclude='data' --exclude='JUCE' --exclude='JUCE_SDK' \
  "$source_root/" "$candidate/"
ln -s "$source_root/.third_party" "$candidate/.third_party"

python3 - "$candidate/VibeAutotune/CorrectionTrajectory.h" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
changes = [
('''                    rendererCrossingProgress = 0.0;
''', '''                    rendererCrossingProgress = 0.0;
                    rendererCrossingExtraHoldSamples = 0;
'''),
('''            if (rendererCrossingProgress >= 1.0
                && currentTargetNote != rendererCrossingTargetNote)
            {
                rendererCrossingActive = false;
                rendererCrossingTargetNote = -1;
            }
''', '''            if (rendererCrossingProgress >= 1.0
                && currentTargetNote != rendererCrossingTargetNote)
            {
                // Diagnostic hypothesis only: hold the existing endpoint for
                // at most 8 ms for selector confirmation, then expire.
                rendererCrossingExtraHoldSamples += elapsedSamples;
                if (rendererCrossingExtraHoldSamples >= static_cast<int> (0.008 * sampleRate))
                {
                    rendererCrossingActive = false;
                    rendererCrossingTargetNote = -1;
                }
            }
'''),
('''    bool rendererCrossingActive = false;
    int rendererCrossingTargetNote = -1;
    double rendererCrossingDurationMs = rendererCrossingTransitionMs;
''', '''    bool rendererCrossingActive = false;
    int rendererCrossingTargetNote = -1;
    int rendererCrossingExtraHoldSamples = 0;
    double rendererCrossingDurationMs = rendererCrossingTransitionMs;
'''),
]
for old, new in changes:
    if s.count(old) != 1:
        raise SystemExit('Candidate source anchor missing or ambiguous; original source was not changed.')
    s = s.replace(old, new, 1)
p.write_text(s)
PY

shasum -a 256 "$source_root/VibeAutotune/CorrectionTrajectory.h" "$candidate/VibeAutotune/CorrectionTrajectory.h" > "$out/source-sha256.txt"
print "Candidate copied to: $candidate"
print 'Running one isolated candidate only; no plug-in will be installed.'
VIBE_ROOT="$candidate" VIBE_HARD_TUNE_CROSSING_WINDOWS_MS=24 \
  zsh "$root/sweep_hook2_tdpsola_renderer_crossing_preview.zsh" | tee "$out/run.log"
print ''
print "CANDIDATE RUN COMPLETE (not installed): $out"
print "Result path is printed as SWEEP COMPLETE above; original source and installed plug-in remain unchanged."
