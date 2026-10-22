#!/bin/zsh
set -euo pipefail

ROOT="${STUDIOFORGE_ROOT:-/Users/hiimdrdey/code/daw}"
SCRIPT_DIR="${0:A:h}"
PLUGIN_ROOT="$ROOT/autotune"
KEEP_BUILD="$PLUGIN_ROOT/build-studioforge-host"

[[ -f "$ROOT/CMakeLists.txt" ]] || { print -u2 "Missing StudioForge source: $ROOT"; exit 1; }
[[ -f "$KEEP_BUILD/CMakeCache.txt" ]] || { print -u2 "Missing canonical VibeAutotune build: $KEEP_BUILD"; exit 1; }

# First produce, install and verify the final DAW plus the canonical AU/VST3.
zsh "$SCRIPT_DIR/package_live_daw_application.zsh"

# The user explicitly requested permanent removal. Every source-tree target is
# an exact allowlisted obsolete build/release path; source and KEEP_BUILD are
# never selected by this cleanup.
typeset -a obsolete_roots
obsolete_roots=(
  "$PLUGIN_ROOT/build-retune-fit"
  "$PLUGIN_ROOT/build-tail-test"
  "$PLUGIN_ROOT/build"
  "$PLUGIN_ROOT/dist"
  "$PLUGIN_ROOT/releases"
)

for target in "${obsolete_roots[@]}"; do
  [[ "$target" == "$KEEP_BUILD" ]] && { print -u2 "Refusing to remove canonical build"; exit 1; }
  [[ "$target" == "$PLUGIN_ROOT"/* ]] || { print -u2 "Unsafe cleanup target: $target"; exit 1; }
  if [[ -e "$target" ]]; then
    rm -rf "$target"
    print "REMOVED: $target"
  fi
done

typeset -a backup_parents
backup_parents=(
  "$HOME/Library/Audio/Plug-Ins/Components"
  "$HOME/Library/Audio/Plug-Ins/VST3"
  "/Users/hiimdrdey/Live daw"
)

for parent in "${backup_parents[@]}"; do
  [[ -d "$parent" ]] || continue
  while IFS= read -r target; do
    case "$target" in
      "$HOME/Library/Audio/Plug-Ins/Components/VibeAutotune Backups"|\
      "$HOME/Library/Audio/Plug-Ins/Components"/VibeAutotune.backup-*.component|\
      "$HOME/Library/Audio/Plug-Ins/VST3"/VibeAutotune.backup-*.vst3|\
      "/Users/hiimdrdey/Live daw"/StudioForge\ Live\ DAW\ backup\ *.app|\
      "/Users/hiimdrdey/Live daw"/Tune-AI\ backup\ *.app)
        rm -rf "$target"
        print "REMOVED: $target"
        ;;
      *)
        print -u2 "Skipped non-allowlisted backup: $target"
        ;;
    esac
  done < <(find "$parent" -maxdepth 1 -type d \
      \( -name 'VibeAutotune Backups' -o -name 'VibeAutotune.backup-*.component' \
         -o -name 'VibeAutotune.backup-*.vst3' -o -name 'StudioForge Live DAW backup *.app' \
         -o -name 'Tune-AI backup *.app' \) -print)
done

for cache_backup in "$HOME/Library/Caches/AudioUnitCache"/com.apple.audiounits.cache.backup-*(N); do
  rm -f "$cache_backup"
  print "REMOVED: $cache_backup"
done

print ""
print "KEPT CANONICAL BUILD: $KEEP_BUILD"
print "KEPT PINNED DEPENDENCIES: $PLUGIN_ROOT/.third_party"
print "KEPT AU:   $HOME/Library/Audio/Plug-Ins/Components/VibeAutotune.component"
print "KEPT VST3: $HOME/Library/Audio/Plug-Ins/VST3/VibeAutotune.vst3"
print "Old VibeAutotune builds and application backups were permanently removed."
