#pragma once

#include <cstdint>

namespace studioforge::link::macos
{
// The deliberately narrow first release contract for the HAL virtual input.
// Supporting only this canonical format avoids hidden format conversion in the
// device callback. A later revision may add a tested converter explicitly.
struct VirtualInputFormat final
{
    double sampleRate = 48000.0;
    std::uint32_t channels = 2;
    std::uint32_t bitsPerSample = 32;
    bool interleaved = true;
    std::uint32_t bufferFrames = 256;

    [[nodiscard]] bool isSupported() const noexcept;
};
}
