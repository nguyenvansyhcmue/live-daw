#!/bin/zsh
# Read-only probe: compiles no production code and never installs a plug-in.
set -euo pipefail

source_dir="/Users/hiimdrdey/code/daw/autotune"
script_dir="${0:A:h}"
artifact_root="${script_dir}/artifacts"
stamp="$(date +%Y%m%d-%H%M%S)"
out_dir="${artifact_root}/live-control-glide-probe-${stamp}"
mkdir -p "${out_dir}"

[[ -f "${source_dir}/VibeAutotune/LiveControlPipeline.h" ]] || {
  print -u2 "Missing VibeAutotune source: ${source_dir}"
  exit 1
}

clang++ -std=c++20 -O0 -I"${source_dir}/VibeAutotune" \
  "${script_dir}/tools/LiveControlGlideProbe.cpp" \
  -o "${out_dir}/LiveControlGlideProbe"

"${out_dir}/LiveControlGlideProbe" | tee "${out_dir}/glide-probe.log"
print ""
print "PROBE COMPLETE (read-only; no VST3 installed): ${out_dir}"
print "Read: ${out_dir}/glide-probe.log"
