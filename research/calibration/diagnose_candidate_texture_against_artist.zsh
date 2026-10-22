#!/bin/zsh
# Read-only analysis of existing bounces. No source, package, or VST3 is modified.
set -euo pipefail
ROOT='/Users/hiimdrdey/autotune'
RAW='/Users/hiimdrdey/Music/Music/Media.localized/Music/Unknown Artist/Unknown Album/hook2_raw_segment.wav'
ARTIST="$ROOT/artifacts/crossing24-bounded-preview-20261017-113218/source/renders/target-autotune-artist.wav"
ORIGINAL="$ROOT/artifacts/verified-legal-adjacency-candidate-20261019-20261019-085158/vibe/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav"
RESIDUAL0="$ROOT/artifacts/legal-adjacency-residual0-20261019-085946/vibe/case_0_retune0.0_flex0.0_humanize0.0_vibrato0.0.wav"
OUT="$ROOT/artifacts/artist-texture-forensics-$(date +%Y%m%d-%H%M%S)"
for f in "$RAW" "$ARTIST" "$ORIGINAL" "$RESIDUAL0"; do [[ -f "$f" ]] || { print -u2 "Missing: $f"; exit 66; }; done
mkdir -p "$OUT"
python3 "$ROOT/tools/diagnose_vocal_texture_ab.py" --raw "$RAW" --artist "$ARTIST" --candidate "$ORIGINAL" --label candidate_original --output "$OUT" | tee "$OUT/original.log"
python3 "$ROOT/tools/diagnose_vocal_texture_ab.py" --raw "$RAW" --artist "$ARTIST" --candidate "$RESIDUAL0" --label candidate_residual0 --output "$OUT" | tee "$OUT/residual0.log"
python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
a = json.loads((root/'candidate_original-texture.json').read_text())
b = json.loads((root/'candidate_residual0-texture.json').read_text())
keys = ['envelope_nrmse_gain_fitted','envelope_correlation','log_magnitude_mae_db','spectral_centroid_median_abs_delta_hz','spectral_flatness_median_abs_delta','high_band_ratio_median_abs_delta_db','modulation_flux_median_abs_delta','short_lag_autocorr_profile_rmse','short_lag_autocorr_max_abs_delta']
rows=['# Artist texture forensics', '', 'Both bounces are independently aligned to the same raw take. Lower is closer except envelope correlation (higher is closer).', '', '| Metric | Original candidate | Residual-off | Direction |', '|---|---:|---:|---|']
for k in keys:
    direction = 'higher closer' if k == 'envelope_correlation' else 'lower closer'
    rows.append(f"| {k} | {a['metrics'][k]:.6f} | {b['metrics'][k]:.6f} | {direction} |")
rows += ['', 'This identifies a differing audible fingerprint; it does not by itself prove a specific DSP mechanism.']
(root/'decision.md').write_text('\n'.join(rows)+'\n')
PY
print "TEXTURE FORENSICS COMPLETE: $OUT"
print "Read first: $OUT/decision.md"
