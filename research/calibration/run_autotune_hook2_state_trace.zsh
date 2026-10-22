#!/bin/zsh
set -euo pipefail

# LLDB halts the target for every breakpoint. Offline render only.
runner='/Users/hiimdrdey/code/daw/build-macos-arm64/StudioForgeCalibrationRunner'
input='/Users/hiimdrdey/Music/Music/Media.localized/Music/Unknown Artist/Unknown Album/hook2_raw_segment.wav'
root='/Users/hiimdrdey/autotune/artifacts'
lldb_script_path='/Users/hiimdrdey/autotune/autotune_hook2_state_trace.lldb'

[[ -x "$runner" ]] || { print -u2 "Missing offline runner: $runner"; exit 1; }
[[ -f "$input" ]] || { print -u2 "Missing Hook 2 WAV: $input"; exit 1; }
[[ -f "$lldb_script_path" ]] || { print -u2 "Missing LLDB command file: $lldb_script_path"; exit 1; }
au_list=$(auval -a)
if ! grep -qi 'Auto-Tune Artist' <<< "$au_list"; then
  if (( $(print -r -- "$au_list" | wc -l) < 6 )); then
    print -u2 'Core Audio returned no registered Audio Units at all (not just Artist); no trace started.'
  else
    print -u2 'Other Audio Units are registered, but Artist is missing; no trace started.'
  fi
  print -u2 "Verify Artist with: auval -v aumf ATxL 'VST '"
  exit 1
fi

trace_dir=$(mktemp -d "$root/artist-hook2-state.XXXXXX")
print "Offline trace: $trace_dir"
print 'Cases include Retune 0, 10, 25, and 50 ms; Alto-Tenor / F# / Natural Minor.'
ARTIST_TRACE_DIR="$trace_dir" \
STUDIOFORGE_CALIBRATION_VOICE='Alto-Tenor' \
STUDIOFORGE_CALIBRATION_KEY='F#' \
STUDIOFORGE_CALIBRATION_SCALE='Natural Minor' \
  lldb -b -s "$lldb_script_path" -- "$runner" "$input" "$trace_dir" 'Auto-Tune Artist' \
  | tee "$trace_dir/lldb.log"

print "Trace events: $trace_dir/events.tsv"
print "Rendered cases: $trace_dir/case_*.wav"
if (( $(wc -l < "$trace_dir/events.tsv") <= 1 )); then
  print -u2 'RENDER COMPLETE, BUT TRACE HAS NO EVENTS. Do not interpret this as DSP state evidence.'
  exit 2
fi
if ! grep -q 'parameterChanged[[:space:]]RetK[[:space:]]' "$trace_dir/events.tsv"; then
  print -u2 'RENDER COMPLETE, BUT NO RetK EVENT WAS CAPTURED. Do not infer Retune state.'
  exit 2
fi
if ! grep -q 'DT_DSPObject[[:space:]]Retune[[:space:]]' "$trace_dir/events.tsv"; then
  print -u2 'RENDER COMPLETE, BUT NO DT DSP SNAPSHOT WAS CAPTURED.'
  exit 2
fi
print 'TRACE PASS: RetK events and DT DSP snapshots captured; inspect case values before interpretation.'
