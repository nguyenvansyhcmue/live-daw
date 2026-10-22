#include "AudioFormat.h"

#include <cmath>

namespace studioforge::link
{
bool AudioFormat::isValid() const noexcept
{
    return std::isfinite(sampleRate) && sampleRate > 0.0 && channelCount > 0;
}
}
