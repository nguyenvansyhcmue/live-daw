#!/bin/zsh
# Diagnostic only; builds the diagnostic in the already-configured candidate
# build. Does not change source, configure flags, sign or install a plugin.
set -euo pipefail
root=/Users/hiimdrdey/autotune
source_root=/Users/hiimdrdey/code/daw/autotune
build="$source_root/build-hook2-tdpsola-crossing-24"
raw="${HOOK2_RAW:-/Users/hiimdrdey/Downloads/hook 2raw.wav}"
out="$root/artifacts/crossing24-worst-transitions-$(date +%Y%m%d-%H%M%S)"
cache="$build/CMakeCache.txt"
[[ -f "$raw" && -f "$cache" ]] || { print -u2 'Missing Hook-2 WAV or candidate build.'; exit 1; }
for flag in 'VIBE_USE_CAUSAL_TDPSOLA_RENDERER_CANDIDATE=1' 'VIBE_HARD_LOCK_RENDERER_CROSSING_TRANSITION_MS=24.0' 'VIBE_ALTO_ANALYSIS_FRAME_SAMPLES=1024' 'VIBE_ALTO_ANALYSIS_HOP_SAMPLES=128'; do
  rg -F -q -- "$flag" "$cache" || { print -u2 "Candidate flag missing: $flag"; exit 1; }
done
mkdir -p "$out"
cmake --build "$build" --target VibeAutotuneSignalChainDiagnostic --parallel 2 | tee "$out/build.log"
diagnostic="$build/VibeAutotuneSignalChainDiagnostic"
shasum -a 256 "$diagnostic" "$cache" "$raw" > "$out/provenance-sha256.txt"
VIBE_DIAGNOSTIC_STEREO_HOST=1 VIBE_DIAGNOSTIC_BLOCK_SIZE=256 VIBE_RAPID_ADJACENT_SELECTOR=1 "$diagnostic" "$raw" "$out" \
  0 1 0 0 0 0 0 0 0 0 0 - 1 > "$out/runner.log"
PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$root/analyze_hook2_selector_delivery.py" "$out" > "$out/delivery-analyser.log"
python3 - "$out/full_default_intervals.csv" "$out/focused-transitions.csv" <<'PY'
import csv, sys

source, dest = sys.argv[1:]
windows = [(0.20, 0.42), (1.50, 1.72), (1.99, 2.25), (3.85, 4.11), (8.22, 8.54)]
with open(source, newline='') as src, open(dest, 'w', newline='') as dst:
    reader = csv.DictReader(src)
    if not reader.fieldnames or 'timeMs' not in reader.fieldnames:
        raise SystemExit('Trace missing timeMs; inspect full_default_intervals.csv')
    writer = csv.DictWriter(dst, fieldnames=reader.fieldnames)
    writer.writeheader()
    for row in reader:
        try: t = float(row['timeMs']) / 1000.0
        except (ValueError, TypeError): continue
        if any(start <= t <= end for start, end in windows):
            writer.writerow(row)
PY
print ''
print "TRACE COMPLETE (diagnostic only; not installed): $out"
print "Windows: $out/focused-transitions.csv"
print "Delivery: $out/selector-delivery-summary.md"
print "Provenance: $out/provenance-sha256.txt"
print "Topology: stereo diagnostic buffer, 256-sample host block; verify its render against the host bounce before interpreting events."
