#include "virtual-device/macos/HalDuplexLoopback.h"

#include <array>
#include <atomic>
#include <cassert>
#include <cmath>
#include <thread>
#include <vector>

using studioforge::link::macos::HalDuplexLoopback;

static void equal(float a, float b) { assert(std::fabs(a - b) < 0.000001f); }

int main()
{
    // Attach first: recorder start never replays audio produced before it opens.
    HalDuplexLoopback loopback(8);
    std::array<float, 2> silence { 1, 1 };
    assert(loopback.read(20, silence.data(), 1) == 0);
    equal(silence[0], 0); equal(silence[1], 0);

    // Impulse/pattern confirms L/R identity and variable callback sizes.
    const std::array<float, 10> written { 1, -1, 0.25f, -0.25f, 0, 0.75f, -0.5f, 0.5f, 0.125f, -0.125f };
    assert(loopback.write(10, written.data(), 5) == 5);
    std::array<float, 4> first {};
    assert(loopback.read(20, first.data(), 2) == 2);
    for (unsigned i = 0; i < 4; ++i) equal(first[i], written[i]);
    std::array<float, 8> second { 9,9,9,9,9,9,9,9 };
    assert(loopback.read(20, second.data(), 4) == 3);
    for (unsigned i = 0; i < 6; ++i) equal(second[i], written[i + 4]);
    equal(second[6], 0); equal(second[7], 0);

    // Two readers retain independent cursors and see the same stereo frames.
    HalDuplexLoopback multiple(16);
    std::array<float, 2> attach {};
    static_cast<void>(multiple.read(21, attach.data(), 1)); static_cast<void>(multiple.read(22, attach.data(), 1));
    const std::array<float, 6> stereo { 2, 20, 3, 30, 4, 40 };
    assert(multiple.write(11, stereo.data(), 3) == 3);
    std::array<float, 6> a {}, b {};
    assert(multiple.read(21, a.data(), 3) == 3);
    assert(multiple.read(22, b.data(), 3) == 3);
    for (unsigned i = 0; i < stereo.size(); ++i) { equal(a[i], stereo[i]); equal(b[i], stereo[i]); }

    // A slow reader bounds the writer; newest frames are rejected, not old
    // unread frames overwritten.
    HalDuplexLoopback bounded(4);
    static_cast<void>(bounded.read(31, attach.data(), 1));
    const std::array<float, 10> overload { 1,10,2,20,3,30,4,40,5,50 };
    assert(bounded.write(12, overload.data(), 5) == 4);
    assert(bounded.overflows() == 1);
    std::array<float, 4> preserved {};
    assert(bounded.read(31, preserved.data(), 2) == 2);
    for (unsigned i = 0; i < preserved.size(); ++i) equal(preserved[i], overload[i]);

    // Advance through the ring, then write a small sine block across its end
    // to validate modulo addressing and stereo continuity.
    std::array<float, 4> sine { 0.0f, 1.0f, static_cast<float>(std::sin(0.5)), static_cast<float>(-std::sin(0.5)) };
    assert(bounded.write(12, sine.data(), 2) == 2);
    std::array<float, 8> wrapped {};
    assert(bounded.read(31, wrapped.data(), 4) == 4);
    equal(wrapped[0], overload[4]); equal(wrapped[1], overload[5]);
    equal(wrapped[2], overload[6]); equal(wrapped[3], overload[7]);
    for (unsigned i = 0; i < sine.size(); ++i) equal(wrapped[i + 4], sine[i]);

    // Writer disconnect invalidates its old timeline, so stale audio cannot
    // replay when an output stream is stopped/reopened.
    multiple.disconnectWriter(11);
    std::array<float, 2> afterDisconnect { 1, 1 };
    assert(multiple.read(21, afterDisconnect.data(), 1) == 0);
    equal(afterDisconnect[0], 0); equal(afterDisconnect[1], 0);

    // Reopening a writer must not replay unread frames from its predecessor.
    HalDuplexLoopback restart(8);
    assert(restart.read(61, attach.data(), 1) == 0);
    assert(restart.write(60, stereo.data(), 3) == 3);
    restart.disconnectWriter(60);
    assert(restart.read(61, attach.data(), 1) == 0);
    equal(attach[0], 0); equal(attach[1], 0);
    const std::array<float, 4> fresh { 7, -7, 8, -8 };
    assert(restart.write(62, fresh.data(), 2) == 2);
    std::array<float, 4> received {};
    assert(restart.read(61, received.data(), 2) == 2);
    for (unsigned i = 0; i < fresh.size(); ++i) equal(received[i], fresh[i]);
    restart.resetWhenStopped();
    assert(restart.read(61, attach.data(), 1) == 0);
    equal(attach[0], 0); equal(attach[1], 0);

    // The ninth concurrent reader is rejected and receives silence; a
    // released reader slot can subsequently be reused.
    HalDuplexLoopback limited(16);
    for (unsigned client = 100; client < 108; ++client)
        assert(limited.read(client, attach.data(), 1) == 0);
    attach = { 1, 1 };
    assert(limited.read(108, attach.data(), 1) == 0);
    assert(limited.rejectedReaders() == 1);
    equal(attach[0], 0); equal(attach[1], 0);
    limited.removeClient(100);
    assert(limited.read(108, attach.data(), 1) == 0);
    assert(limited.rejectedReaders() == 1);

    // Deterministic concurrent writer/reader exercise: each frame encodes a
    // relation that must survive wraparound and independently scheduled blocks.
    HalDuplexLoopback concurrent(1024);
    static_cast<void>(concurrent.read(41, attach.data(), 1));
    std::atomic<bool> finished { false };
    std::atomic<unsigned> checked { 0 };
    std::thread producer([&]
    {
        std::array<float, 32> block {};
        for (unsigned n = 0; n < 4000; ++n)
        {
            for (unsigned frame = 0; frame < 16; ++frame) { block[frame * 2] = static_cast<float>(n * 16 + frame); block[frame * 2 + 1] = -block[frame * 2]; }
            static_cast<void>(concurrent.write(40, block.data(), 16));
        }
        finished.store(true, std::memory_order_release);
    });
    std::thread consumer([&]
    {
        std::array<float, 14> block {};
        while (!finished.load(std::memory_order_acquire) || checked.load(std::memory_order_relaxed) < 32)
        {
            const auto count = concurrent.read(41, block.data(), 7);
            for (std::size_t frame = 0; frame < count; ++frame) { equal(block[frame * 2 + 1], -block[frame * 2]); checked.fetch_add(1, std::memory_order_relaxed); }
        }
    });
    producer.join(); consumer.join();
    assert(checked.load(std::memory_order_relaxed) > 0);

    // Exercise reader churn while the writer wraps the storage. This is also
    // useful under ThreadSanitizer; it does not emulate the Core Audio host.
    HalDuplexLoopback churn(16);
    std::atomic<bool> start { false };
    std::thread churnWriter([&]
    {
        std::array<float, 32> block {};
        while (!start.load(std::memory_order_acquire)) {}
        for (unsigned n = 0; n < 200000; ++n)
        {
            for (unsigned i = 0; i < 16; ++i) { block[2*i] = static_cast<float>(n); block[2*i+1] = -block[2*i]; }
            static_cast<void>(churn.write(50, block.data(), 16));
        }
    });
    std::thread churnReader([&]
    {
        std::array<float, 16> block {};
        start.store(true, std::memory_order_release);
        for (unsigned n = 0; n < 200000; ++n)
        {
            static_cast<void>(churn.read(51, block.data(), 8));
            if ((n % 3) == 0) churn.removeClient(51);
        }
    });
    churnWriter.join(); churnReader.join();

    // Generation changes while capture is running must not race sample
    // storage; TSAN checks the overlap even when a timing assertion cannot.
    HalDuplexLoopback generations(16);
    std::atomic<bool> go { false };
    std::thread restartingWriter([&]
    {
        std::array<float, 32> block {};
        while (!go.load(std::memory_order_acquire)) {}
        for (unsigned n = 0; n < 100000; ++n)
        {
            block.fill(static_cast<float>(n));
            static_cast<void>(generations.write(70, block.data(), 16));
            if ((n % 3) == 0) generations.disconnectWriter(70);
        }
    });
    std::thread generationReader([&]
    {
        std::array<float, 16> block {};
        go.store(true, std::memory_order_release);
        for (unsigned n = 0; n < 100000; ++n)
            static_cast<void>(generations.read(71, block.data(), 8));
    });
    restartingWriter.join(); generationReader.join();
}
