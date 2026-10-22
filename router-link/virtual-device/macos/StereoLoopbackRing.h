#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace studioforge::link::macos
{
// Fixed-capacity, single-producer/single-consumer transport used at the two
// real-time sides of the first HAL virtual device. Samples are interleaved
// Float32 stereo frames: L, R, L, R ... . Construct and destroy it while both
// HAL streams are stopped. Exactly one writer (the virtual device output
// stream) and one reader (the virtual device input stream) may call it.
//
// write() never overwrites unread audio: excess newest frames are rejected.
// read() always supplies the caller's requested block, zero-filling an
// underrun. Neither method allocates, locks, waits or calls into Core Audio.
class StereoLoopbackRing final
{
public:
    explicit StereoLoopbackRing(std::size_t capacityFrames);

    [[nodiscard]] std::size_t capacityFrames() const noexcept { return capacity; }
    [[nodiscard]] std::size_t availableToRead() const noexcept;
    [[nodiscard]] std::size_t availableToWrite() const noexcept;

    [[nodiscard]] std::size_t write(const float* interleavedStereo, std::size_t frames) noexcept;
    // Returns the count of real frames copied. The remaining requested frames
    // are silence, which prevents stale audio becoming visible to a recorder.
    [[nodiscard]] std::size_t read(float* interleavedStereo, std::size_t frames) noexcept;

    // Stop both streams before clearing; this is not a callback operation.
    void clearWhenStopped() noexcept;

private:
    void copyInto(std::uint64_t firstFrame, const float* input, std::size_t frames) noexcept;
    void copyOut(std::uint64_t firstFrame, float* output, std::size_t frames) noexcept;

    const std::size_t capacity;
    std::vector<float> samples;
    // Monotonic counters avoid ambiguity when reader == writer. They are only
    // changed by their respective SPSC owner and must remain lock-free.
    std::atomic<std::uint64_t> readFrame { 0 };
    std::atomic<std::uint64_t> writeFrame { 0 };
};
}
