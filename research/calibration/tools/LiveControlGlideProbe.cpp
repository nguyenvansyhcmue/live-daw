#include "LiveControlPipeline.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>

namespace
{
constexpr double sampleRate = 48000.0;
constexpr int tick = 64;

NotePolicySnapshot chromaticPolicy()
{
    NotePolicySnapshot policy;
    policy.pitchClassDefaults.fill (NoteRule::Legal);
    policy.midiNoteOverrides.fill (NoteRule::Legal);
    return policy;
}

double frequencyForCents (double cents)
{
    return 440.0 * std::exp2 (cents / 1200.0);
}

double centsForRatio (double ratio)
{
    return 1200.0 * std::log2 (std::max (ratio, 1.0e-12));
}
}

int main()
{
    LiveControlPipeline live;
    live.prepare (sampleRate, tick);
    const auto policy = chromaticPolicy();

    LiveControlParameters parameters;
    parameters.retuneSpeedMs = 20.0;
    parameters.flexTunePercent = 0.0;

    auto previousRatio = 1.0;
    auto previousTarget = -1;
    auto maxRatioStep = 0.0;

    std::cout << std::fixed << std::setprecision (6);
    for (int sample = 0; sample < static_cast<int> (0.45 * sampleRate); sample += tick)
    {
        const auto t = static_cast<double> (sample) / (0.45 * sampleRate);
        const auto inputCents = -60.0 + 240.0 * std::clamp (t, 0.0, 1.0);
        const auto observed = live.observePitch (frequencyForCents (inputCents), true, false,
                                                 parameters, policy);
        const auto advanced = live.advance();
        const auto step = std::abs (advanced.pitchRatio - previousRatio);
        maxRatioStep = std::max (maxRatioStep, step);

        if (step >= 0.004 || advanced.targetChanged || advanced.targetNote != previousTarget)
        {
            std::cout << "glide_probe"
                      << " sample=" << sample
                      << " input_cents=" << inputCents
                      << " observed_target=" << observed.targetNote
                      << " advanced_target=" << advanced.targetNote
                      << " target_changed=" << advanced.targetChanged
                      << " observed_correction=" << observed.correctionCents
                      << " advanced_correction=" << advanced.correctionCents
                      << " advanced_ratio=" << advanced.pitchRatio
                      << " ratio_step=" << step
                      << " step_cents=" << std::abs (centsForRatio (advanced.pitchRatio)
                                                        - centsForRatio (previousRatio))
                      << '\n';
        }

        previousRatio = advanced.pitchRatio;
        previousTarget = advanced.targetNote;
    }

    std::cout << "glide_probe_summary max_ratio_step=" << maxRatioStep << '\n';
}
