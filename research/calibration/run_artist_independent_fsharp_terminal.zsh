#!/bin/zsh
set -euo pipefail

# Run from the user's normal macOS Terminal, which can see registered Audio Units.
# This is diagnostic only and never replaces an installed plug-in or DAW app.
runner='/Users/hiimdrdey/code/daw/build-macos-arm64/StudioForgeCalibrationRunner'
input='/Users/hiimdrdey/Library/Application Support/StudioForge/Research/GTSinger/English/EN-Tenor-1/Glissando/All I Ask/Glissando_Group/0001.wav'
output_parent='/Users/hiimdrdey/autotune/artifacts/gtsinger-qualified-return-ab-20261021'

[[ -x "$runner" ]] || { print -u2 "Missing StudioForge runner: $runner"; exit 1; }
[[ -f "$input" ]] || { print -u2 "Missing independent vocal fixture: $input"; exit 1; }
au_list=$(auval -a)
if ! grep -qi 'Auto-Tune Artist' <<< "$au_list"; then
  print -u2 'Auto-Tune Artist is not registered in this Terminal session; no render started.'
  exit 1
fi

output=$(mktemp -d "$output_parent/artist-fsharp-terminal.XXXXXX")
print "Artist render output: $output"
print "Runner SHA-256: $(shasum -a 256 "$runner" | awk '{print $1}')"
print "Input SHA-256: $(shasum -a 256 "$input" | awk '{print $1}')"
print 'Settings: Alto-Tenor / F# / Natural Minor; case 0 has all four controls at zero.'

STUDIOFORGE_CALIBRATION_VOICE='Alto-Tenor' \
STUDIOFORGE_CALIBRATION_KEY='F#' \
STUDIOFORGE_CALIBRATION_SCALE='Natural Minor' \
  "$runner" "$input" "$output" 'Auto-Tune Artist' > "$output/runner.log" 2>&1 || {
    print -u2 "Artist render failed; inspect $output/runner.log"
    tail -n 30 "$output/runner.log" >&2
    exit 1
  }

[[ -s "$output/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav" ]] || {
  print -u2 "Runner exited without a hard-tune-zero WAV; inspect $output/runner.log"
  exit 1
}
print "Artist render complete: $output"
print "Hard-tune zero: $output/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav"
