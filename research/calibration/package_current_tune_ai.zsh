#!/bin/zsh
# Package the current Tune-AI source as a self-contained macOS app.  The
# existing app is replaced only after the staged package matches source hashes
# and passes signing verification.
set -euo pipefail

SOURCE='/Users/hiimdrdey/code/daw/tune-AI'
LIVE_ROOT='/Users/hiimdrdey/Live daw'
DESTINATION="$LIVE_ROOT/Tune-AI.app"
INFO_PLIST='/Users/hiimdrdey/autotune/Tune-AI-Info.plist'
LAUNCHER='/Users/hiimdrdey/autotune/tune_ai_macos_launcher.zsh'
STAMP=$(date +%Y%m%d-%H%M%S)
STAGE="/private/tmp/Tune-AI-$STAMP.app"

[[ -f "$SOURCE/main.py" ]] || { print -u2 "Tune-AI source is missing: $SOURCE/main.py"; exit 1; }
[[ -x "$SOURCE/.venv/bin/python3" ]] || { print -u2 "Tune-AI venv is missing: $SOURCE/.venv/bin/python3"; exit 1; }
[[ -f "$INFO_PLIST" && -f "$LAUNCHER" ]] || { print -u2 'Tune-AI packaging templates are missing.'; exit 1; }
[[ -d "$LIVE_ROOT" ]] || { print -u2 "Live DAW folder is missing: $LIVE_ROOT"; exit 1; }

cleanup_stage() { [[ -e "$STAGE" ]] && rm -rf "$STAGE"; }
trap cleanup_stage EXIT

mkdir -p "$STAGE/Contents/MacOS" "$STAGE/Contents/Resources/tune-AI"
ditto "$INFO_PLIST" "$STAGE/Contents/Info.plist"
ditto "$LAUNCHER" "$STAGE/Contents/MacOS/Tune-AI"
chmod 755 "$STAGE/Contents/MacOS/Tune-AI"

for item in main.py daw_bridge.py core ui assets data native; do
  [[ -e "$SOURCE/$item" ]] && ditto "$SOURCE/$item" "$STAGE/Contents/Resources/tune-AI/$item"
done
ditto "$SOURCE/.venv" "$STAGE/Contents/Resources/tune-AI/.venv"

# A venv created by Homebrew often has an absolute Python symlink.  App bundles
# reject that form, so copy the real interpreter and recreate local links.
REAL_PYTHON=$("$SOURCE/.venv/bin/python3" -c 'import os, sys; print(os.path.realpath(sys.executable))')
VENV_BIN="$STAGE/Contents/Resources/tune-AI/.venv/bin"
PYTHON_NAME="${REAL_PYTHON:t}"
[[ -x "$REAL_PYTHON" ]] || { print -u2 "Resolved Python is not executable: $REAL_PYTHON"; exit 1; }
rm -f "$VENV_BIN/python" "$VENV_BIN/python3" "$VENV_BIN/$PYTHON_NAME"
ditto "$REAL_PYTHON" "$VENV_BIN/$PYTHON_NAME"
chmod 755 "$VENV_BIN/$PYTHON_NAME"
ln -s "$PYTHON_NAME" "$VENV_BIN/python3"
ln -s python3 "$VENV_BIN/python"

# A distributable bundle must not retain links to the source machine.
while IFS= read -r link; do
  target=$(readlink "$link")
  [[ "$target" != /* ]] || { print -u2 "Refusing absolute symlink in package: $link -> $target"; exit 1; }
done < <(find "$STAGE" -type l -print)

SOURCE_MAIN_SHA=$(shasum -a 256 "$SOURCE/main.py" | awk '{print $1}')
STAGED_MAIN_SHA=$(shasum -a 256 "$STAGE/Contents/Resources/tune-AI/main.py" | awk '{print $1}')
[[ "$SOURCE_MAIN_SHA" == "$STAGED_MAIN_SHA" ]] || { print -u2 'Staged Tune-AI main.py differs from source.'; exit 1; }

codesign --force --deep --sign - "$STAGE"
codesign --verify --deep --strict "$STAGE"

if [[ -e "$DESTINATION" ]]; then
  BACKUP="$LIVE_ROOT/Tune-AI backup $STAMP.app"
  mv "$DESTINATION" "$BACKUP"
  print "Previous Tune-AI package moved to: $BACKUP"
fi
mv "$STAGE" "$DESTINATION"
trap - EXIT

PACKAGED_MAIN_SHA=$(shasum -a 256 "$DESTINATION/Contents/Resources/tune-AI/main.py" | awk '{print $1}')
[[ "$SOURCE_MAIN_SHA" == "$PACKAGED_MAIN_SHA" ]] || { print -u2 'Installed Tune-AI main.py verification failed.'; exit 1; }
codesign --verify --deep --strict "$DESTINATION"

print ''
print 'TUNE-AI CURRENT PACKAGE CREATED'
print "Source main.py SHA-256:   $SOURCE_MAIN_SHA"
print "Packaged main.py SHA-256: $PACKAGED_MAIN_SHA"
print "App: $DESTINATION"
print 'Open with:'
print "  open '$DESTINATION'"
