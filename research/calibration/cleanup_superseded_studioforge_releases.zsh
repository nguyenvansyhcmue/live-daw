#!/bin/zsh
# Move only superseded StudioForge/Tune-AI release bundles to Trash after the
# current packaged release and its embedded Vibe binary are verified.
set -euo pipefail

LIVE_ROOT='/Users/hiimdrdey/Live daw'
DIST_ROOT='/Users/hiimdrdey/code/daw/dist'
APP="$LIVE_ROOT/StudioForge Live DAW.app"
TUNE_APP="$LIVE_ROOT/Tune-AI.app"
TUNE_SOURCE='/Users/hiimdrdey/code/daw/tune-AI'
INSTALLED_VST3='/Users/hiimdrdey/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3'
EMBEDDED_VST3="$APP/Contents/Resources/PlugIns/VST3/VibeAutotune.vst3"
TRASH='/Users/hiimdrdey/.Trash'
STAMP=$(date +%Y%m%d-%H%M%S)

[[ -d "$APP" ]] || { print -u2 "Current packaged DAW is missing: $APP"; exit 1; }
[[ -d "$TUNE_APP" ]] || { print -u2 "Current Tune-AI app is missing: $TUNE_APP"; exit 1; }
[[ -f "$TUNE_SOURCE/main.py" && -f "$TUNE_APP/Contents/Resources/tune-AI/main.py" ]] || {
  print -u2 'Tune-AI source or packaged main.py is missing; refusing cleanup.'; exit 1;
}
[[ -d "$INSTALLED_VST3" && -d "$EMBEDDED_VST3" ]] || {
  print -u2 'Current installed or embedded VibeAutotune is missing.'; exit 1;
}
codesign --verify --deep --strict "$APP"
codesign --verify --deep --strict "$INSTALLED_VST3"
codesign --verify --deep --strict "$EMBEDDED_VST3"

installed_sha=$(shasum -a 256 "$INSTALLED_VST3/Contents/MacOS/VibeAutotune" | awk '{print $1}')
embedded_sha=$(shasum -a 256 "$EMBEDDED_VST3/Contents/MacOS/VibeAutotune" | awk '{print $1}')
[[ "$installed_sha" == "$embedded_sha" ]] || {
  print -u2 'Current DAW does not embed the verified installed VST3; refusing cleanup.'; exit 1;
}

tune_source_sha=$(shasum -a 256 "$TUNE_SOURCE/main.py" | awk '{print $1}')
tune_packaged_sha=$(shasum -a 256 "$TUNE_APP/Contents/Resources/tune-AI/main.py" | awk '{print $1}')
[[ "$tune_source_sha" == "$tune_packaged_sha" ]] || {
  print -u2 'Tune-AI.app is not the current source revision; package it before cleanup.'; exit 1;
}

typeset -a targets
targets=()
while IFS= read -r -d '' path; do targets+=("$path"); done < <(
  find "$LIVE_ROOT" -mindepth 1 -maxdepth 1 -type d \( \
    -name 'StudioForge Live DAW backup*.app' -o \
    -name 'StudioForge Live DAW.backup-*.app' -o \
    -name 'StudioForge Live DAW lỗi*.app' -o \
    -name 'Tune-AI backup*.app' \
  \) -print0
)
while IFS= read -r -d '' path; do targets+=("$path"); done < <(
  find "$DIST_ROOT" -mindepth 1 -maxdepth 1 -type d -name 'StudioForge Live DAW*.app' -print0 2>/dev/null
)
while IFS= read -r -d '' path; do targets+=("$path"); done < <(
  find '/Users/hiimdrdey/Library/Audio/Plug-Ins/VST3' -mindepth 1 -maxdepth 1 -type d \
    \( -name 'VibeAutotune.backup-*.vst3' -o -name 'VibeAutotune.vst3.*' \) -print0
)
while IFS= read -r -d '' path; do targets+=("$path"); done < <(
  find '/Users/hiimdrdey/Library/Audio/Plug-Ins/Components' -mindepth 1 -maxdepth 1 -type d \
    \( -name 'VibeAutotune.backup-*.component' -o -name 'VibeAutotune.component.backup*' \) -print0
)
while IFS= read -r -d '' path; do targets+=("$path"); done < <(
  find "$APP/Contents/Resources/PlugIns/VST3" -mindepth 1 -maxdepth 1 -type d \
    -name 'VibeAutotune.backup-*.vst3' -print0
)

(( ${#targets[@]} > 0 )) || { print 'No superseded release bundles found.'; exit 0; }
mkdir -p "$TRASH"
print "Verified retained DAW and VST3 SHA-256: $installed_sha"
print "Verified retained Tune-AI main.py SHA-256: $tune_source_sha"
print "Moving ${#targets[@]} superseded bundle(s) to Trash:"
for target in "${targets[@]}"; do
  [[ "$target" != "$APP" && "$target" != "$TUNE_APP" && "$target" != "$INSTALLED_VST3" && "$target" != "$EMBEDDED_VST3" ]] || {
    print -u2 "Refusing protected target: $target"; exit 1;
  }
  name="${target:t}"
  destination="$TRASH/${name:r}.studioforge-superseded-$STAMP.${name:e}"
  mv "$target" "$destination"
  print "  moved: $target"
done
print ''
print 'Cleanup complete. Bundles were moved to Trash and can be recovered there.'
