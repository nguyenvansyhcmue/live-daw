#include "virtual-device/macos/StereoLoopbackRing.h"

#include <cassert>
#include <cmath>
#include <vector>

using studioforge::link::macos::StereoLoopbackRing;

static void same(const float actual, const float expected)
{
    assert(std::fabs(actual - expected) < 0.000001f);
}

int main()
{
    StereoLoopbackRing ring(4);
    assert(ring.capacityFrames() == 4);
    const float initial[] { 1, 10, 2, 20, 3, 30 };
    assert(ring.write(initial, 3) == 3);
    assert(ring.availableToRead() == 3);

    float first[4] {};
    assert(ring.read(first, 2) == 2);
    same(first[0], 1); same(first[1], 10); same(first[2], 2); same(first[3], 20);

    // Wrap the preallocated ring and retain stereo identity.
    const float wrapped[] { 4, 40, 5, 50, 6, 60 };
    assert(ring.write(wrapped, 3) == 3);
    float afterWrap[8] {};
    assert(ring.read(afterWrap, 4) == 4);
    const float expected[] { 3, 30, 4, 40, 5, 50, 6, 60 };
    for (unsigned i = 0; i < 8; ++i) same(afterWrap[i], expected[i]);

    // Bounded overload drops new frames rather than growing or overwriting
    // unread PCM; underruns return deterministically silent tail samples.
    const float overload[] { 7, 70, 8, 80, 9, 90, 10, 100, 11, 110 };
    assert(ring.write(overload, 5) == 4);
    assert(ring.write(overload, 1) == 0);
    float partial[12] { 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99 };
    assert(ring.read(partial, 6) == 4);
    for (unsigned frame = 0; frame < 4; ++frame) {
        same(partial[frame * 2], overload[frame * 2]);
        same(partial[frame * 2 + 1], overload[frame * 2 + 1]);
    }
    for (unsigned i = 8; i < 12; ++i) same(partial[i], 0);

    ring.clearWhenStopped();
    assert(ring.availableToRead() == 0);
    float silence[2] { 1, 1 };
    assert(ring.read(silence, 1) == 0);
    same(silence[0], 0); same(silence[1], 0);
}
