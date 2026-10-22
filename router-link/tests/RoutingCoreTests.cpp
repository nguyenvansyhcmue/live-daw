#include "core/RoutingCore.h"

#include <array>
#include <cmath>
#include <iostream>
#include <limits>
#include <thread>

using namespace studioforge::link;
namespace
{
bool check(bool value, const char* name) { if (! value) std::cerr << "FAIL: " << name << '\n'; return value; }
bool near(float a, float b) { return std::abs(a - b) < 0.00001f; }
}
int main()
{
    constexpr std::size_t n = 64;
    RoutingConfig config;
    config.endpoints = { { 1, EndpointKind::source }, { 2, EndpointKind::source },
                         { 3, EndpointKind::bus }, { 4, EndpointKind::destination }, { 5, EndpointKind::destination },
                         { 6, EndpointKind::bus } };
    if (! check(config.addRoute({ 1, 3 }) && config.addRoute({ 2, 3 })
                && config.addRoute({ 3, 4 }) && config.addRoute({ 3, 5 }), "create routes")) return 1;
    if (! check(! config.addRoute({ 5, 1 }) && ! config.addRoute({ 999, 4 }) && ! config.addRoute({ 1, 3 })
                && ! config.addRoute({ 3, 3 }), "invalid routes rejected")) return 1;
    if (! check(config.addRoute({ 3, 6 }) && ! config.addRoute({ 6, 3 }) && config.removeRoute(3, 6), "cycle rejected")) return 1;
    std::string error;
    RoutingConfig restored;
    if (! check(RoutingConfig::deserialize(config.serialize(), restored, error) && restored.serialize() == config.serialize(), "persistence round trip")) return 1;
    const auto saved = restored.serialize();
    if (! check(! RoutingConfig::deserialize("STUDIOFORGE_LINK 1\n1 0\n0 0\n", restored, error)
                && restored.serialize() == saved, "invalid persistence is transactional")) return 1;
    RoutingCore core(6, 8, n);
    if (! check(core.publish(restored, error), "publish")) return 1;
    std::array<float, n> l {}, r {}, second {}, outL {}, outR {}, otherL {}, otherR {};
    for (std::size_t i = 0; i < n; ++i) { l[i] = std::sin(static_cast<float>(i) * 0.1f); r[i] = -0.25f * l[i]; second[i] = 0.125f; }
    InputBlock input[] { { 1, l.data(), r.data(), n }, { 2, second.data(), nullptr, n / 2 } };
    OutputBlock output[] { { 4, outL.data(), outR.data(), n }, { 5, otherL.data(), otherR.data(), n } };
    if (! check(core.process(input, 2, output, 2, n), "process")) return 1;
    for (std::size_t i = 0; i < n; ++i)
        if (! check(near(outL[i], l[i] + (i < n / 2 ? second[i] : 0.0f)) && near(outR[i], r[i])
                    && near(otherL[i], outL[i]) && near(otherR[i], outR[i]), "sine stereo mix and independent destinations")) return 1;
    restored.routes[0].channelMap = { 1, 0 }; restored.routes[0].gain = 0.5f;
    restored.routes[1].muted = true;
    if (! check(core.publish(restored, error) && core.process(input, 2, output, 2, n), "republish")) return 1;
    for (std::size_t i = 0; i < n; ++i)
        if (! check(near(outL[i], r[i] * 0.5f) && near(outR[i], l[i] * 0.5f), "channel map gain mute")) return 1;
    if (! check(restored.removeRoute(3, 5) && core.publish(restored, error) && core.process(input, 2, output, 2, n), "remove route")) return 1;
    if (! check(near(otherL[7], 0.0f) && near(otherR[7], 0.0f), "removed destination silence")) return 1;
    outL.fill(42.0f); outR.fill(42.0f); output[0].frames = 7;
    if (! check(! core.process(input, 2, output, 2, n + 1) && outL[6] == 0.0f && outL[7] == 42.0f, "oversize clears only valid output")) return 1;
    output[0].frames = n;
    if (! check(core.process(nullptr, 0, output, 2, n) && near(outL[3], 0.0f) && near(outR[3], 0.0f), "missing source silence")) return 1;
    restored.routes[0].gain = std::numeric_limits<float>::quiet_NaN();
    if (! check(! core.publish(restored, error), "invalid gain rejected")) return 1;
    RoutingConfig concurrent;
    concurrent.endpoints = { { 11, EndpointKind::source }, { 12, EndpointKind::destination } };
    concurrent.routes = { { 11, 12 } };
    RoutingCore live(2, 1, n);
    if (! check(live.publish(concurrent, error), "initial concurrent configuration")) return 1;
    std::atomic<bool> good { true };
    std::thread publisher([&] {
        std::string localError;
        for (int i = 0; i < 10000; ++i)
        {
            concurrent.routes[0].gain = i % 2 ? 1.0f : 2.0f;
            if (! live.publish(concurrent, localError)) good.store(false);
        }
    });
    std::array<float, n> ones, left {}, right {}; ones.fill(1.0f);
    InputBlock liveInput { 11, ones.data(), ones.data(), n };
    OutputBlock liveOutput { 12, left.data(), right.data(), n };
    for (int i = 0; i < 10000; ++i)
    {
        if (! live.process(&liveInput, 1, &liveOutput, 1, n)) good.store(false);
        const auto expected = left[0];
        for (std::size_t frame = 0; frame < n; ++frame)
            if ((expected != 1.0f && expected != 2.0f) || left[frame] != expected || right[frame] != expected)
                good.store(false);
    }
    publisher.join();
    if (! check(good.load(), "concurrent block-boundary publication")) return 1;
    return 0;
}
