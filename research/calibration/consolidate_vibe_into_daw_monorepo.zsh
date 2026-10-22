#!/bin/zsh
# Consolidate the already-pushed VibeAutotune repository into StudioForge DAW.
# This intentionally imports source history as one subtree snapshot; generated
# build output is excluded by the source repository's .gitignore.
set -euo pipefail

DAW_ROOT="${DAW_ROOT:-/Users/hiimdrdey/code/daw}"
VIBE_REMOTE="${VIBE_REMOTE:-https://github.com/nguyenvansyhcmue/aututun.git}"
BRANCH="${BRANCH:-main}"

[[ -d "$DAW_ROOT/.git" ]] || { print -u2 "Not a DAW Git repository: $DAW_ROOT"; exit 1; }
cd "$DAW_ROOT"

# The local nested checkout is not tracked by daw. Preserve it so subtree can
# create the tracked autotune/ directory and so no experiment is lost.
if [[ -d autotune ]]; then
  backup="${DAW_ROOT:h}/daw-autotune-local-backup-$(date +%Y%m%d-%H%M%S)"
  mv autotune "$backup"
  print "Preserved local Vibe checkout: $backup"
fi

git subtree add --prefix=autotune "$VIBE_REMOTE" "$BRANCH" --squash \
  -m "feat: import VibeAutotune into StudioForge monorepo"

# StudioForge must fetch exact public dependencies itself.  Do not depend on
# the nested repo's accidental gitlinks or on developer-machine SDK folders.
python3 - <<'PY'
from pathlib import Path
p = Path('CMakeLists.txt')
s = p.read_text()
old = '''# Vibe's production renderer is header-only but its CMake targets carry the
# platform math dependency (Accelerate on macOS). Share those exact pinned
# sources with the native StudioForge adapter.
if (NOT TARGET signalsmith-linear)
    add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/autotune/.third_party/signalsmith_linear-src"
                     "${CMAKE_CURRENT_BINARY_DIR}/signalsmith-linear")
endif()
if (NOT TARGET signalsmith-stretch)
    add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/autotune/.third_party/signalsmith_stretch-src"
                     "${CMAKE_CURRENT_BINARY_DIR}/signalsmith-stretch")
endif()
'''
new = '''# Vibe renderer dependencies: fixed public revisions downloaded by CMake.
# This keeps a fresh StudioForge clone self-contained and reproducible.
FetchContent_Declare(signalsmith_linear
    GIT_REPOSITORY https://github.com/Signalsmith-Audio/linear.git
    GIT_TAG 5668673560146a9cfe38c25315071e3fd68c8317
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(signalsmith_linear)

FetchContent_Declare(signalsmith_stretch
    GIT_REPOSITORY https://github.com/Signalsmith-Audio/signalsmith-stretch.git
    GIT_TAG 57b93f4e9206a089a45387eaa39bdc9f310d3308
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(signalsmith_stretch)
'''
if old not in s:
    raise SystemExit('CMake dependency block changed; no files were modified.')
p.write_text(s.replace(old, new))
PY

cat >> .gitignore <<'EOF'

# VibeAutotune generated output and local dependency overrides
/autotune/artifacts/
/autotune/artist-renders/
/autotune/build*/
/autotune/VibeAutotune/build/
/autotune/.third_party/
EOF

git add CMakeLists.txt .gitignore autotune
git commit -m "build: consolidate VibeAutotune in reproducible StudioForge monorepo"
git push origin "$BRANCH"

print "\nDONE: StudioForge + VibeAutotune are now in one Git repository."
print "Verify from a fresh clone with: cmake -S . -B build -DCMAKE_BUILD_TYPE=Release"
