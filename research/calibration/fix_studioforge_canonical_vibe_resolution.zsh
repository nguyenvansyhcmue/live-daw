#!/bin/zsh
# Make the packaged VibeAutotune the sole canonical Vibe for StudioForge.
# This prevents duplicate system/user/backup VST3 copies sharing one UID from
# winning enumeration order over the approved plug-in embedded in the app.
set -euo pipefail

ROOT='/Users/hiimdrdey/code/daw'
TOOLS='/Users/hiimdrdey/autotune'
PATCH="$TOOLS/studioforge_canonical_bundled_vibe.patch"
SCANNER_PATCH="$TOOLS/studioforge_bundled_vibe_scanner.patch"

if pgrep -x 'StudioForge DAW' >/dev/null 2>&1; then
  print -u2 'StudioForge DAW is running. Save, quit it completely, then rerun this command.'
  exit 2
fi

[[ -f "$PATCH" ]] || { print -u2 "Missing patch: $PATCH"; exit 1; }
[[ -f "$SCANNER_PATCH" ]] || { print -u2 "Missing patch: $SCANNER_PATCH"; exit 1; }
[[ -f "$ROOT/Source/Control/PitchCorrectionIntegrationService.cpp" ]] || { print -u2 "StudioForge source not found: $ROOT"; exit 1; }

if ! rg -q 'bundledVibeAutotune\(\)' "$ROOT/Source/Control/PitchCorrectionIntegrationService.cpp"; then
  patch --batch --forward -p1 -d "$ROOT" < "$PATCH"
  print 'Applied canonical bundled-Vibe host policy.'
else
  print 'Canonical bundled-Vibe host policy already applied.'
fi

if ! rg -q 'packagedProbe' "$ROOT/Source/Plugins/PluginHostService.cpp"; then
  patch --batch --forward -p1 -d "$ROOT" < "$SCANNER_PATCH"
  print 'Applied self-contained bundled VST3 scanner fix.'
else
  print 'Self-contained bundled VST3 scanner fix already applied.'
fi

# Delete all Vibe entries, including nested legacy entries.  The next app boot
# scans only Contents/Resources/PlugIns/VST3/VibeAutotune.vst3 for this product.
zsh "$TOOLS/repair_studioforge_vibe_catalog.zsh"

# Rebuild and package the host with the approved DSP binary and provenance.
zsh "$TOOLS/promote_approved_vibe_to_studioforge.zsh"

catalog="$HOME/Library/StudioForge/PluginCatalog.xml"
if [[ -f "$catalog" ]] && rg -qi 'name="VibeAutotune"' "$catalog"; then
  print -u2 'Catalog still contains Vibe entries; refusing to claim completion.'
  exit 1
fi
print 'PASS: StudioForge now pins Auto Key/Vocal Vibe to its bundled approved VST3.'
