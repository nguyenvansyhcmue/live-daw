#pragma once

#include <cstdint>

namespace studioforge::link
{
// A negotiated stream format, not a device choice or a routing graph.
// Frame count is intentionally absent: callback sizes may vary per block.
struct AudioFormat
{
    double sampleRate = 0.0;
    std::uint32_t channelCount = 0;

    [[nodiscard]] bool isValid() const noexcept;
};
}
