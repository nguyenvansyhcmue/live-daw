#!/bin/zsh
# Applies only the LiveControlPipeline handoff repair, then builds and runs
# its focused proof. It does not install or sign a VST3.
set -euo pipefail

source_dir="/Users/hiimdrdey/code/daw/autotune"
script_dir="${0:A:h}"
build_dir="${source_dir}/build-hook2-tdpsola-crossing-24"

[[ -f "${source_dir}/VibeAutotune/LiveControlPipeline.h" ]] || {
  print -u2 "Missing VibeAutotune source: ${source_dir}"
  exit 1
}
[[ -d "${build_dir}" ]] || {
  print -u2 "Missing candidate build directory: ${build_dir}"
  exit 1
}

if rg -q "maximumRendererCorrectionStepCents" "${source_dir}/VibeAutotune/LiveControlPipeline.h"; then
  print "Already applied: Live Control output de-zipper"
else
  # Generate the patch from the file that is actually present. This avoids
  # brittle line-number hunks when earlier diagnostics have changed it.
  temp_dir="$(mktemp -d)"
  trap 'rm -rf "${temp_dir}"' EXIT
  original="${source_dir}/VibeAutotune/LiveControlPipeline.h"
  candidate="${temp_dir}/LiveControlPipeline.h"
  cp "${original}" "${candidate}"
  python3 - "${candidate}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()

reset_old = """        trajectory.reset();
        last = {};
        haveTrajectory = false;
"""
reset_new = """        trajectory.reset();
        last = {};
        haveTrajectory = false;
        deliveredCorrectionCents = 0.0;
        haveDeliveredCorrection = false;
"""

advance_old = """        const auto data = trajectory.advanceScheduledTransition (controlIntervalSamples, sampleRate);
        last = fromTrajectory (data, last.stableF0Hz, last.voiced, false);
        haveTrajectory = data.hasValidCorrection;
"""
advance_new = """        const auto data = trajectory.advanceScheduledTransition (controlIntervalSamples, sampleRate);
        last = fromTrajectory (data, last.stableF0Hz, last.voiced, false);
        dezipperRendererControl (last);
        haveTrajectory = data.hasValidCorrection;
"""

private_old = """private:
    static LiveControlFrame fromTrajectory"""
private_new = """private:
    // Musical target selection remains untouched. This last handoff limiter
    // prevents a newly published pitch-centre state becoming a grain-control
    // discontinuity. 16 cents stays below a 1% ratio step per control tick.
    static constexpr double maximumRendererCorrectionStepCents = 16.0;

    void dezipperRendererControl (LiveControlFrame& frame) noexcept
    {
        if (! frame.valid || ! std::isfinite (frame.correctionCents))
            return;

        if (! haveDeliveredCorrection)
        {
            deliveredCorrectionCents = frame.correctionCents;
            haveDeliveredCorrection = true;
        }
        else
        {
            const auto delta = std::clamp (frame.correctionCents - deliveredCorrectionCents,
                                           -maximumRendererCorrectionStepCents,
                                            maximumRendererCorrectionStepCents);
            deliveredCorrectionCents += delta;
        }

        frame.correctionCents = deliveredCorrectionCents;
        frame.pitchRatio = std::exp2 (deliveredCorrectionCents / 1200.0);
    }

    static LiveControlFrame fromTrajectory"""

fields_old = """    LiveControlFrame last;
    bool haveTrajectory = false;
};
"""
fields_new = """    LiveControlFrame last;
    bool haveTrajectory = false;
    double deliveredCorrectionCents = 0.0;
    bool haveDeliveredCorrection = false;
};
"""

for old, new in ((reset_old, reset_new), (advance_old, advance_new),
                 (private_old, private_new), (fields_old, fields_new)):
    if old not in text:
        raise SystemExit("Source anchor missing; no source files changed.")
    text = text.replace(old, new, 1)

path.write_text(text)
PY
  generated_patch="${temp_dir}/live-control-output-dezipper.patch"
  # BSD Git on this machine does not accept git-diff's --label form with
  # --no-index. Generate a standard unified diff, then make its paths
  # relative to the source root for git apply.
  diff -u "${original}" "${candidate}" > "${generated_patch}" || {
    diff_status=$?
    [[ ${diff_status} -eq 1 ]] || exit ${diff_status}
  }
  perl -0pi -e 's!\A--- [^\n]*\n\+\+\+ [^\n]*!--- a/VibeAutotune/LiveControlPipeline.h\n+++ b/VibeAutotune/LiveControlPipeline.h!' "${generated_patch}"
  [[ -s "${generated_patch}" ]] || {
    print -u2 "Generated patch was empty; no source files changed."
    exit 1
  }
  git -C "${source_dir}" apply --check "${generated_patch}"
  git -C "${source_dir}" apply "${generated_patch}"
  print "Applied: Live Control output de-zipper"
fi

cmake --build "${build_dir}" --target VibeAutotuneLiveControlPipelineTest -j2
"${build_dir}/VibeAutotuneLiveControlPipelineTest"
print ""
print "PASS: focused Live Control proof completed. No plug-in was installed."
