#!/bin/zsh
# Diagnostic only: explicit candidate VST3 against the existing Artist bounces.
set -euo pipefail
workspace="${GTSINGER_WORKSPACE:-/Users/hiimdrdey/autotune}"
root="${GTSINGER_BENCHMARK_ROOT:-$HOME/Library/Application Support/StudioForge/Research/GTSinger}"
daw="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
runner="${STUDIOFORGE_CALIBRATION_RUNNER:-$daw/build-macos-arm64/StudioForgeCalibrationRunner}"
candidate="${VIBE_CANDIDATE_VST3:-$workspace/artifacts/crossing24-bounded-preview-20261017-113341/source/build-hook2-tdpsola-crossing-24/VibeAutotune_artefacts/Release/VST3/VibeAutotune.vst3}"
old_run="${GTSINGER_ARTIST_REFERENCE_RUN:-$root/runs/artist-vibe-ab-20261017-144126}"
tools="${PITCH_TOOLS:-$workspace/artifacts/crossing24-bounded-preview-20261017-113341/source/tools}"
output="${GTSINGER_EXPLICIT_OUTPUT:-$workspace/artifacts/gtsinger-explicit-vst3-$(date +%Y%m%d-%H%M%S)}"
exe="$candidate/Contents/MacOS/VibeAutotune"
analyser="$daw/Tools/analyze_studioforge_calibration.py"
[[ -x "$runner" && -f "$exe" && -f "$analyser" && -f "$tools/compare_pitch_correction_bounces.py" ]] || { print -u2 'Missing runner, explicit candidate VST3, analyser, or pitch tools.'; exit 66; }
[[ ! -e "$output" ]] || { print -u2 "Output already exists: $output"; exit 73; }
mkdir -p "$output"
{
  print 'Candidate is an experimental bounded-preview build, not a promoted release.'
  print "Candidate: $candidate"
  print "Runner: $runner"
  print "Artist reference run: $old_run"
  print 'Expected settings: Alto / F / Natural Minor; Retune/Flex/Humanize/Vibrato zero for case 0.'
  print 'Previous Artist reference did not record a binary hash or exact displayed parameter readbacks; comparisons are exploratory.'
  shasum -a 256 "$exe" "$runner"
} > "$output/provenance.txt"

for clip in 0001 0002; do
  input="$root/English/EN-Alto-1/Glissando/for the first time in forever/Glissando_Group/$clip.wav"
  reference="$old_run/Glissando-for_the_first_time_in_forever-$clip-Glissando_Group/artist/calibration-report.csv"
  job="$output/$clip"
  [[ -f "$input" && -f "$reference" ]] || { print -u2 "Missing clip or Artist reference: $clip"; exit 66; }
  mkdir -p "$job/vibe"
  print "Rendering explicit VST3: Glissando $clip"
  shasum -a 256 "$input" >> "$output/provenance.txt"
  env STUDIOFORGE_CALIBRATION_VOICE=Alto STUDIOFORGE_CALIBRATION_KEY=F STUDIOFORGE_CALIBRATION_SCALE='Natural Minor' \
    "$runner" "$input" "$job/vibe" VibeAutotune "$candidate" > "$job/runner.log" 2>&1 || {
      print -u2 "Render failed; inspect $job/runner.log"; exit 1
    }
  # Confirm the scanned catalog is explicitly VST3, never the default AU.
  rg -q 'name="VibeAutotune" format="VST3"' "$job/vibe/StudioForgeCalibrationPluginCatalog.xml" || {
    print -u2 "Catalog did not confirm VST3; inspect $job/vibe/StudioForgeCalibrationPluginCatalog.xml"; exit 1
  }
  awk -F, 'NR==1 || ($2==0 && $3==0 && $4==0 && $5==0)' "$job/vibe/calibration-report.csv" > "$job/vibe-zero.csv"
  awk -F, 'NR==1 || ($2==0 && $3==0 && $4==0 && $5==0)' "$reference" > "$job/artist-zero.csv"
  PYTHONPATH="$tools${PYTHONPATH:+:$PYTHONPATH}" PYTHONPYCACHEPREFIX=/private/tmp/python-cache python3 "$analyser" \
    "$input" "$job/vibe-zero.csv" "$job/artist-zero.csv" "$job/comparison"
done
print "EXPLORATORY A/B COMPLETE (not installed): $output"
print "Provenance: $output/provenance.txt"
print 'Read each clip comparison/calibration-report.md; confirm actual parameter readback before promotion.'
