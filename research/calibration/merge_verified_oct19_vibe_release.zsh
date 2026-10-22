#!/bin/zsh
# Promote the verified production Vibe source as the Oct-19 release baseline.
#
# The annotated-fricative verification did NOT approve a new DSP gate, high-band
# handoff, or renderer experiment.  It approved keeping the production DSP
# unchanged and proved that the large +5.60 dB "S" result belonged to a
# rejected research snapshot.  The only uncommitted plugin changes that belong
# in this release are the piano/manual-selection UI persistence fixes.
set -euo pipefail

TOOLS_ROOT='/Users/hiimdrdey/autotune'
BUILD_ROOT='/Users/hiimdrdey/code/daw-autotune-local-backup-20261017-132903'
MONOREPO_ROOT='/Users/hiimdrdey/code/daw/autotune'
EDITOR_CPP='VibeAutotune/PluginEditor.cpp'
EDITOR_H='VibeAutotune/PluginEditor.h'
TAG='vibe-verified-production-2026-10-19'

[[ -d "$BUILD_ROOT/.git" ]] || { print -u2 "Missing canonical Vibe Git source: $BUILD_ROOT"; exit 1; }
[[ -f "$MONOREPO_ROOT/$EDITOR_CPP" ]] || { print -u2 "Missing StudioForge Vibe mirror: $MONOREPO_ROOT"; exit 1; }

if pgrep -x 'StudioForge DAW' >/dev/null 2>&1; then
  print -u2 'Quit StudioForge DAW completely before merging and packaging this release.'
  exit 2
fi

# Refuse to hide someone else's tracked work.  The source contains many old
# untracked diagnostic notes/reject files; they stay untracked and untouched.
changed=$(git -C "$BUILD_ROOT" diff --name-only)
if [[ -n "$changed" ]]; then
  unexpected=$(print -r -- "$changed" | grep -v -E "^(${EDITOR_CPP}|${EDITOR_H})$" || true)
  [[ -z "$unexpected" ]] || {
    print -u2 'Refusing to merge: unrelated tracked source edits are present:'
    print -u2 -- "$unexpected"
    exit 1
  }
fi
git -C "$BUILD_ROOT" diff --cached --quiet || {
  print -u2 'Refusing to merge: the canonical Vibe source already has staged changes.'
  exit 1
}
git -C "$BUILD_ROOT" diff --check -- "$EDITOR_CPP" "$EDITOR_H"

# These two files are the approved latest UI state.  The audio DSP remains the
# existing production implementation; do not copy any rejected research tree.
for relative in "$EDITOR_CPP" "$EDITOR_H"; do
  cmp -s "$BUILD_ROOT/$relative" "$MONOREPO_ROOT/$relative" || cp "$BUILD_ROOT/$relative" "$MONOREPO_ROOT/$relative"
done

git -C "$BUILD_ROOT" add -- "$EDITOR_CPP" "$EDITOR_H"
if git -C "$BUILD_ROOT" diff --cached --quiet; then
  print 'Canonical source already contains the verified Oct-19 UI state; no new source commit needed.'
else
  git -C "$BUILD_ROOT" commit -m 'release: checkpoint verified Vibe production baseline' \
    -m 'Keep the approved production DSP. Do not promote rejected sibilance gate/high-band experiments. Persist manual piano selection in the UI.'
fi

if git -C "$BUILD_ROOT" rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  print "Release tag already exists: $TAG"
else
  git -C "$BUILD_ROOT" tag -a "$TAG" -m 'Verified production Vibe baseline; annotated fricative check found no DSP change to promote.'
fi

# This rebuilds Vibe from exactly the committed canonical source, embeds that
# binary in StudioForge, and verifies the installed/embedded hashes match.
zsh "$TOOLS_ROOT/promote_approved_vibe_to_studioforge.zsh"

print ''
print 'MERGE + PACKAGE COMPLETE'
print "Canonical commit: $(git -C "$BUILD_ROOT" rev-parse --short=12 HEAD)"
print "Release tag:      $TAG"
print 'DSP policy:       production DSP preserved; rejected sibilance experiments excluded.'
