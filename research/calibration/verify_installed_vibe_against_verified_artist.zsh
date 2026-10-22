#!/bin/zsh
# Strict one-case A/B verification.  It measures the actually installed Vibe
# VST3 bounce against the checksum-pinned Artist target, not a historical CSV.
set -euo pipefail

WORK=/Users/hiimdrdey/autotune
DAW=/Users/hiimdrdey/code/daw
TOOLS="$WORK/artifacts/crossing24-bounded-preview-20261017-113218/source/tools"
RAW='/Users/hiimdrdey/Music/Music/Media.localized/Music/Unknown Artist/Unknown Album/hook2_raw_segment.wav'
VIBE="$WORK/artifacts/hook2-installed-vibe-ab-20261019-081605/vibe/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav"
ARTIST="$WORK/artifacts/crossing24-bounded-preview-20261017-113218/source/renders/target-autotune-artist.wav"
EXPECTED_RAW=c241b07c23528541960b45ca4889a1ae105200ab9ba1a4a239c81683f98bac28
EXPECTED_ARTIST=fe8fcafac41f18fe7c5b823e52bf94b988fcf1a0270e93722bfe4db5a21caadb
OUT="$WORK/artifacts/installed-vibe-verified-artist-ab-$(date +%Y%m%d-%H%M%S)"

[[ -f "$RAW" && -f "$VIBE" && -f "$ARTIST" && -d "$TOOLS" ]] || { print -u2 'Missing raw, installed-bounce, verified Artist target, or analyzer tools.'; exit 1; }
[[ "$(shasum -a 256 "$RAW" | awk '{print $1}')" == "$EXPECTED_RAW" ]] || { print -u2 'Raw checksum mismatch.'; exit 1; }
[[ "$(shasum -a 256 "$ARTIST" | awk '{print $1}')" == "$EXPECTED_ARTIST" ]] || { print -u2 'Artist checksum mismatch.'; exit 1; }
mkdir -p "$OUT"
printf 'case,retune_ms,flex_tune,humanize,natural_vibrato,output\n0,0,0,0,0,"%s"\n' "$VIBE" > "$OUT/vibe.csv"
printf 'case,retune_ms,flex_tune,humanize,natural_vibrato,output\n0,0,0,0,0,"%s"\n' "$ARTIST" > "$OUT/artist.csv"
PYTHONPATH="$TOOLS${PYTHONPATH:+:$PYTHONPATH}" \
  python3 "$DAW/Tools/analyze_studioforge_calibration.py" "$RAW" "$OUT/vibe.csv" "$OUT/artist.csv" "$OUT/comparison"

cat > "$OUT/provenance.md" <<EOF
# Provenance

- Raw SHA-256: $EXPECTED_RAW
- Artist target SHA-256: $EXPECTED_ARTIST
- Vibe input: $VIBE
- Vibe binary SHA-256: 0eea517d9e1647d0d848f08702742a8ef034fe5f72921c16b8124ef91f6c0a63
- Preset: Alto / F# Natural Minor / Retune 0 / Flex 0 / Humanize 0 / Natural Vibrato 0
EOF
print "VERIFIED A/B COMPLETE: $OUT"
print "Read: $OUT/comparison/calibration-report.md"
