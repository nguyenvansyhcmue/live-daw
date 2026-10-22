#!/bin/zsh
# Repair an installed local-development AU bundle whose CodeResources seal was
# made stale by a manual copy. This never changes DSP sources or parameters.
set -euo pipefail

component="$HOME/Library/Audio/Plug-Ins/Components/VibeAutotune.component"
[[ -d "$component" ]] || { print -u2 "missing component: $component"; exit 66; }

/usr/bin/codesign --force --deep --sign - "$component"
/usr/bin/codesign --verify --deep --strict --verbose=2 "$component"
rm -f "$HOME/Library/Caches/AudioUnitCache/com.apple.audiounits.cache"
killall -9 AudioComponentRegistrar 2>/dev/null || true

print "AU bundle signature repaired. Quit Logic completely, reopen it, then validate:"
print "  auval -v aufx Atun VbAu"
