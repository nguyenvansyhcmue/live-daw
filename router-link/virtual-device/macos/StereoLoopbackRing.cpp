#include "virtual-device/macos/StereoLoopbackRing.h"

#include <algorithm>
#include <cstring>

namespace studioforge::link::macos
{
static_assert(std::atomic<std::uint64_t>::is_always_lock_free,
              "HAL transport requires lock-free 64-bit atomics");

StereoLoopbackRing::StereoLoopbackRing(const std::size_t capacityFrames)
    : capacity(std::max<std::size_t>(1, capacityFrames)), samples(capacity * 2, 0.0f)
{
}

std::size_t StereoLoopbackRing::availableToRead() const noexcept
{
    const auto written = writeFrame.load(std::memory_order_acquire);
    const auto read = readFrame.load(std::memory_order_relaxed);
    return static_cast<std::size_t>(std::min<std::uint64_t>(written - read, capacity));
}

std::size_t StereoLoopbackRing::availableToWrite() const noexcept
{
    return capacity - availableToRead();
}

void StereoLoopbackRing::copyInto(const std::uint64_t firstFrame, const float* input,
                                  const std::size_t frames) noexcept
{
    const auto index = static_cast<std::size_t>(firstFrame % capacity);
    const auto first = std::min(frames, capacity - index);
    std::memcpy(samples.data() + index * 2, input, first * 2 * sizeof(float));
    if (first != frames)
        std::memcpy(samples.data(), input + first * 2, (frames - first) * 2 * sizeof(float));
}

void StereoLoopbackRing::copyOut(const std::uint64_t firstFrame, float* output,
                                 const std::size_t frames) noexcept
{
    const auto index = static_cast<std::size_t>(firstFrame % capacity);
    const auto first = std::min(frames, capacity - index);
    std::memcpy(output, samples.data() + index * 2, first * 2 * sizeof(float));
    if (first != frames)
        std::memcpy(output + first * 2, samples.data(), (frames - first) * 2 * sizeof(float));
}

std::size_t StereoLoopbackRing::write(const float* const interleavedStereo,
                                      const std::size_t requestedFrames) noexcept
{
    if (interleavedStereo == nullptr || requestedFrames == 0) return 0;
    const auto writable = availableToWrite();
    const auto frames = std::min(requestedFrames, writable);
    if (frames == 0) return 0;
    const auto start = writeFrame.load(std::memory_order_relaxed);
    copyInto(start, interleavedStereo, frames);
    writeFrame.store(start + frames, std::memory_order_release);
    return frames;
}

std::size_t StereoLoopbackRing::read(float* const interleavedStereo,
                                     const std::size_t requestedFrames) noexcept
{
    if (interleavedStereo == nullptr || requestedFrames == 0) return 0;
    const auto readable = availableToRead();
    const auto frames = std::min(requestedFrames, readable);
    if (frames != 0)
    {
        const auto start = readFrame.load(std::memory_order_relaxed);
        copyOut(start, interleavedStereo, frames);
        readFrame.store(start + frames, std::memory_order_release);
    }
    if (frames != requestedFrames)
        std::memset(interleavedStereo + frames * 2, 0, (requestedFrames - frames) * 2 * sizeof(float));
    return frames;
}

void StereoLoopbackRing::clearWhenStopped() noexcept
{
    std::fill(samples.begin(), samples.end(), 0.0f);
    readFrame.store(0, std::memory_order_relaxed);
    writeFrame.store(0, std::memory_order_relaxed);
}
}
