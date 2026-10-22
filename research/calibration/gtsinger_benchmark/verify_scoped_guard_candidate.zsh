#!/bin/zsh
# Verify (and only when explicitly requested, apply) the measured scoped guard.
# This never installs, signs, or replaces a plug-in binary.
set -euo pipefail

script_dir=${0:A:h}
patch_file="$script_dir/experimental_periodic_guard.patch"
source_dir=${VIBE_SOURCE_DIR:-/Users/hiimdrdey/code/daw/autotune}
build_dir=${VIBE_BUILD_DIR:-}

[[ -f "$patch_file" ]] || { print -u2 "Missing patch: $patch_file"; exit 1; }
[[ -f "$source_dir/VibeAutotune/PluginProcessor.cpp" ]] || {
  print -u2 "VIBE_SOURCE_DIR is not a VibeAutotune source tree: $source_dir"; exit 1
}

repo_root=$(git -C "$source_dir" rev-parse --show-toplevel)
source_prefix=$(git -C "$source_dir" rev-parse --show-prefix)
apply_cmd=(git -C "$repo_root" apply)
[[ -n "$source_prefix" ]] && apply_cmd+=(--directory="${source_prefix%/}")

if "${apply_cmd[@]}" --reverse --check "$patch_file" 2>/dev/null; then
  print "STATUS: candidate patch is already applied in $source_dir"
  already_applied=1
else
  "${apply_cmd[@]}" --check "$patch_file"
  print "STATUS: candidate patch applies cleanly to $source_dir"
  already_applied=0
fi

print "PATCH_SHA256: $(shasum -a 256 "$patch_file" | awk '{ print $1 }')"
print "SCOPE: voiced low-band exception + protected noise-floor update + 5 ms renderer re-entry hold"
print "INSTALL: none (this verifier never signs or copies a VST3/AU)"

if [[ ${VIBE_APPLY_CANDIDATE:-0} == 1 && $already_applied == 0 ]]; then
  "${apply_cmd[@]}" "$patch_file"
  print "APPLIED: source only; rebuild, run tests, and listen before installation."
fi

if [[ -n "$build_dir" ]]; then
  [[ -d "$build_dir" ]] || { print -u2 "VIBE_BUILD_DIR does not exist: $build_dir"; exit 1; }
  cmake --build "$build_dir" --target \
    VibeAutotuneKeyScaleLivePathTest \
    VibeAutotuneCausalTDPSOLATest \
    VibeAutotuneLiveControlPipelineTest -j 4
  "$build_dir/VibeAutotuneKeyScaleLivePathTest"
  "$build_dir/VibeAutotuneCausalTDPSOLATest"
  "$build_dir/VibeAutotuneLiveControlPipelineTest"
fi
