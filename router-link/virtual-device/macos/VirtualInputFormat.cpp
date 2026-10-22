#include "virtual-device/macos/VirtualInputFormat.h"

namespace studioforge::link::macos
{
bool VirtualInputFormat::isSupported() const noexcept
{
    const bool supportedRate = sampleRate == 44100.0 || sampleRate == 48000.0;
    // The HAL property implementation will publish this exact range. Keeping
    // the maximum finite lets the preallocated ring be sized before StartIO.
    return supportedRate && channels == 2 && bitsPerSample == 32 && interleaved
        && bufferFrames >= 64 && bufferFrames <= 1024;
}
}
