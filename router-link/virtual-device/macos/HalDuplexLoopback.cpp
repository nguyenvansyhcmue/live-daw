#include "virtual-device/macos/HalDuplexLoopback.h"

#include <algorithm>
#include <cstring>

namespace studioforge::link::macos
{
static_assert(std::atomic<std::uint64_t>::is_always_lock_free);
static_assert(std::atomic<std::uint32_t>::is_always_lock_free);
constexpr std::uint32_t kAttachingReader = UINT32_MAX;

HalDuplexLoopback::HalDuplexLoopback(const std::size_t capacityFrames)
    : capacity(std::max<std::size_t>(1, capacityFrames)), samples(capacity * 2, 0.0f) {}

HalDuplexLoopback::Reader* HalDuplexLoopback::findOrAttach(const std::uint32_t client) noexcept
{
    if (client == 0) return nullptr;
    for (auto& reader : readers)
        if (reader.client.load(std::memory_order_acquire) == client) return &reader;
    for (auto& reader : readers)
    {
        std::uint32_t empty = 0;
        if (reader.client.compare_exchange_strong(empty, kAttachingReader, std::memory_order_acq_rel))
        {
            // Publish cursor and epoch before publishing this slot to writer
            // callbacks. A transient attaching sentinel is not an active
            // reader and cannot make a callback observe uninitialised state.
            reader.cursor.store(writeCursor.load(std::memory_order_acquire), std::memory_order_relaxed);
            reader.generation.store(timelineGeneration.load(std::memory_order_acquire), std::memory_order_relaxed);
            reader.client.store(client, std::memory_order_release);
            return &reader;
        }
    }
    rejectedReaderCount.fetch_add(1, std::memory_order_relaxed);
    return nullptr;
}

void HalDuplexLoopback::copyIn(const std::uint64_t cursor, const float* input, const std::size_t frames) noexcept
{
    const auto at = static_cast<std::size_t>(cursor % capacity);
    const auto first = std::min(frames, capacity - at);
    std::memcpy(samples.data() + at * 2, input, first * 2 * sizeof(float));
    if (first != frames) std::memcpy(samples.data(), input + first * 2, (frames - first) * 2 * sizeof(float));
}

void HalDuplexLoopback::copyOut(const std::uint64_t cursor, float* output, const std::size_t frames) noexcept
{
    const auto at = static_cast<std::size_t>(cursor % capacity);
    const auto first = std::min(frames, capacity - at);
    std::memcpy(output, samples.data() + at * 2, first * 2 * sizeof(float));
    if (first != frames) std::memcpy(output + first * 2, samples.data(), (frames - first) * 2 * sizeof(float));
}

std::size_t HalDuplexLoopback::write(const std::uint32_t client, const float* const stereo, const std::size_t requested) noexcept
{
    if (client == 0 || stereo == nullptr || requested == 0) return 0;
    auto owner = writerClient.load(std::memory_order_acquire);
    if (owner == 0)
    {
        if (! writerClient.compare_exchange_strong(owner, client, std::memory_order_acq_rel)) return 0;
        owner = client;
    }
    if (owner != client) return 0;

    const auto write = writeCursor.load(std::memory_order_relaxed);
    const auto generation = timelineGeneration.load(std::memory_order_acquire);
    auto minimumRead = write;
    bool hasReader = false;
    for (const auto& reader : readers)
        if (reader.client.load(std::memory_order_acquire) != 0
            && reader.generation.load(std::memory_order_acquire) == generation)
        {
            hasReader = true;
            minimumRead = std::min(minimumRead, reader.cursor.load(std::memory_order_acquire));
        }
    const auto used = hasReader ? write - minimumRead : 0;
    const auto free = used >= capacity ? 0 : capacity - static_cast<std::size_t>(used);
    const auto accepted = std::min(requested, free);
    if (accepted != requested) overflowFrames.fetch_add(requested - accepted, std::memory_order_relaxed);
    if (accepted == 0) return 0;
    copyIn(write, stereo, accepted);
    writeCursor.store(write + accepted, std::memory_order_release);
    return accepted;
}

std::size_t HalDuplexLoopback::read(const std::uint32_t client, float* const stereo, const std::size_t requested) noexcept
{
    if (stereo == nullptr || requested == 0) return 0;
    auto* reader = findOrAttach(client);
    if (reader == nullptr) { std::memset(stereo, 0, requested * 2 * sizeof(float)); return 0; }
    const auto generation = timelineGeneration.load(std::memory_order_acquire);
    if (reader->generation.load(std::memory_order_acquire) != generation)
    {
        reader->cursor.store(writeCursor.load(std::memory_order_acquire), std::memory_order_release);
        reader->generation.store(generation, std::memory_order_release);
        std::memset(stereo, 0, requested * 2 * sizeof(float));
        underrunFrames.fetch_add(requested, std::memory_order_relaxed);
        return 0;
    }
    const auto read = reader->cursor.load(std::memory_order_relaxed);
    const auto write = writeCursor.load(std::memory_order_acquire);
    const auto available = std::min<std::uint64_t>(write - read, capacity);
    const auto copied = std::min(requested, static_cast<std::size_t>(available));
    if (copied != 0) { copyOut(read, stereo, copied); reader->cursor.store(read + copied, std::memory_order_release); }
    if (copied != requested)
    {
        std::memset(stereo + copied * 2, 0, (requested - copied) * 2 * sizeof(float));
        underrunFrames.fetch_add(requested - copied, std::memory_order_relaxed);
    }
    return copied;
}

void HalDuplexLoopback::removeClient(const std::uint32_t client) noexcept
{
    for (auto& reader : readers)
        if (reader.client.load(std::memory_order_acquire) == client)
            reader.client.store(0, std::memory_order_release);
}

void HalDuplexLoopback::disconnectWriter(const std::uint32_t client) noexcept
{
    auto owner = client;
    if (writerClient.compare_exchange_strong(owner, 0, std::memory_order_acq_rel))
        timelineGeneration.fetch_add(1, std::memory_order_acq_rel);
}

void HalDuplexLoopback::resetWhenStopped() noexcept
{
    writerClient.store(0, std::memory_order_release);
    timelineGeneration.fetch_add(1, std::memory_order_acq_rel);
    for (auto& reader : readers) reader.client.store(0, std::memory_order_release);
}
}
