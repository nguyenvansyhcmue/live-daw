#!/bin/zsh
# Atomic bootstrap for the AU diagnostic calibration only.
# It refuses to run a sweep unless the installed component is byte-identical
# to the build artifact that exposes the two diagnostic parameters.
set -euo pipefail

if (( $# != 1 )); then
  print -u2 "usage: $0 /absolute/path/to/raw.wav"
  exit 64
fi

raw=${1:A}
root=/Users/hiimdrdey/code/daw
built="$root/autotune/build-retune-fit/VibeAutotune_artefacts/Release/AU/VibeAutotune.component"
installed="$HOME/Library/Audio/Plug-Ins/Components/VibeAutotune.component"
backup="$HOME/Library/Audio/Plug-Ins/Components/VibeAutotune.pre-knot-calibration.component"
runner="$root/build-calibration-arm64/StudioForgeCalibrationRunner"

[[ -f $raw ]] || { print -u2 "missing raw WAV: $raw"; exit 66; }
[[ -x $runner ]] || { print -u2 "missing runner: $runner"; exit 1; }

# AU parameter schemas are cached by macOS under the bundle version. This is
# a diagnostic-only 1.0.7 build so the two newly-added parameters are visible
# to the host instead of reusing the 1.0.6 schema.
if ! rg -q 'project\(VibeAutotuneProj VERSION 1\.0\.7' "$root/autotune/CMakeLists.txt"; then
  git -C "$root" apply /Users/hiimdrdey/autotune/vibe-retune-knot-au-version.patch
fi

cmake -S "$root/autotune" -B "$root/autotune/build-retune-fit" \
  -G "Unix Makefiles" \
  -DCMAKE_BUILD_TYPE=Release \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_LINEAR="$root/autotune/build/_deps/signalsmith_linear-src" \
  -DFETCHCONTENT_SOURCE_DIR_SIGNALSMITH_STRETCH="$root/autotune/build/_deps/signalsmith_stretch-src"
cmake --build "$root/autotune/build-retune-fit" --target VibeAutotune_AU --parallel 8
cmake --build "$root/build-calibration-arm64" --target StudioForgeCalibrationRunner --parallel 8

[[ -f "$built/Contents/MacOS/VibeAutotune" ]] || { print -u2 "missing built AU: $built"; exit 1; }

# CMake's linker signature covers the Mach-O, but a copied AU bundle can
# retain an obsolete CodeResources manifest.  Core Audio will then silently
# omit it from the registry (and a DAW may keep using an old cached instance).
# Re-sign the whole bundle before it is copied and fail closed if it is not a
# valid local/ad-hoc AU bundle.
/usr/bin/codesign --force --deep --sign - "$built"
/usr/bin/codesign --verify --deep --strict --verbose=2 "$built"

# Do not use grep -q under pipefail: grep exits early then strings receives
# SIGPIPE, turning a successful match into a false negative.
strings "$built/Contents/MacOS/VibeAutotune" | grep -F 'Diagnostic Retune 10 T90' >/dev/null \
  || { print -u2 "build artifact does not contain the diagnostic AU parameters"; exit 1; }

# Preserve one recoverable copy. The exact installed bundle is then removed
# so ditto cannot silently merge an old nested bundle or stale executable.
if [[ -d $installed && ! -e $backup ]]; then
  mv "$installed" "$backup"
fi
rm -rf "$installed"
ditto --rsrc --extattr --acl "$built" "$installed"

# Verify the installed bundle as well: a byte-identical executable alone is
# insufficient when CodeResources/Info.plist sealing is stale.
/usr/bin/codesign --verify --deep --strict --verbose=2 "$installed"

builtHash=$(shasum "$built/Contents/MacOS/VibeAutotune" | awk '{print $1}')
installedHash=$(shasum "$installed/Contents/MacOS/VibeAutotune" | awk '{print $1}')
print "build SHA:     $builtHash"
print "installed SHA: $installedHash"
[[ $builtHash == $installedHash ]] || { print -u2 "install verification failed"; exit 1; }

killall -9 AudioComponentRegistrar 2>/dev/null || true
rm -f "$HOME/Library/Caches/AudioUnitCache/com.apple.audiounits.cache"
rm -f "$root"/retune-knot-fit/t10-*/StudioForgeCalibrationPluginCatalog.xml(N)

print "AU install verified; launching diagnostic sweep."
exec zsh /Users/hiimdrdey/autotune/run_retune_knot_sweep.sh "$raw"
