#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace studioforge::link::macos
{
// Fixed-storage HAL transport: one output-stream writer and up to eight input
// stream clients. Each reader owns a cursor, so a recorder never consumes data
// belonging to another recorder. Construction/destruction happen off the HAL
// real-time threads; read/write/attach/detach do not allocate or block.
class HalDuplexLoopback final
{
public:
    static constexpr std::size_t maxReaders = 8;
    explicit HalDuplexLoopback(std::size_t capacityFrames);

    // Only one output client may write. A new writer invalidates old audio;
    // it is intentionally not a mixer.
    [[nodiscard]] std::size_t write(std::uint32_t client, const float* stereo, std::size_t frames) noexcept;
    [[nodiscard]] std::size_t read(std::uint32_t client, float* stereo, std::size_t frames) noexcept;
    void removeClient(std::uint32_t client) noexcept;
    void disconnectWriter(std::uint32_t client) noexcept;
    void resetWhenStopped() noexcept;

    [[nodiscard]] std::uint64_t underruns() const noexcept { return underrunFrames.load(std::memory_order_relaxed); }
    [[nodiscard]] std::uint64_t overflows() const noexcept { return overflowFrames.load(std::memory_order_relaxed); }
    [[nodiscard]] std::uint64_t rejectedReaders() const noexcept { return rejectedReaderCount.load(std::memory_order_relaxed); }

private:
    struct Reader { std::atomic<std::uint32_t> client { 0 }; std::atomic<std::uint64_t> cursor { 0 }; std::atomic<std::uint64_t> generation { 0 }; };
    Reader* findOrAttach(std::uint32_t client) noexcept;
    void copyIn(std::uint64_t cursor, const float* stereo, std::size_t frames) noexcept;
    void copyOut(std::uint64_t cursor, float* stereo, std::size_t frames) noexcept;

    const std::size_t capacity;
    std::vector<float> samples;
    std::array<Reader, maxReaders> readers;
    std::atomic<std::uint32_t> writerClient { 0 };
    std::atomic<std::uint64_t> writeCursor { 0 };
    // Incrementing this invalidates every reader's old timeline without
    // touching the sample buffer while a callback could still access it.
    std::atomic<std::uint64_t> timelineGeneration { 1 };
    std::atomic<std::uint64_t> underrunFrames { 0 }, overflowFrames { 0 }, rejectedReaderCount { 0 };
};
}
