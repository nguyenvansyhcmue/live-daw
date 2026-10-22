#include "LiveBridgeControllerTests.h"
#include "Control/LiveBridgeController.h"

#include <cassert>

namespace {
struct Provider final : LiveBridgeEndpointProvider {
    std::vector<LiveBridgeEndpoint> endpoints; std::string failure;
    std::vector<LiveBridgeEndpoint> discover(std::string& error) const override { error = failure; return endpoints; }
};
struct Port final : LiveBridgeOutputPort {
    double rate = 48000.0; bool open = false; std::uint64_t callbacks = 0; std::string connected; bool reject = false;
    int connectCalls = 0;
    double primarySampleRate() const override { return rate; }
    bool connectUid(const std::string& uid, std::string& error) override { ++connectCalls; if (reject) { error = "open failed"; return false; } connected = uid; open = true; return true; }
    void disconnect() override { open = false; connected.clear(); }
    bool configured() const override { return open; }
    std::uint64_t callbackCount() const override { return callbacks; }
};
}

bool runLiveBridgeControllerTests()
{
    assert(normaliseLiveBridgeEndpointUid("  com.example.virtual  ") == "com.example.virtual");
    assert(normaliseLiveBridgeEndpointUid("bad\nuid").empty());
    assert(normaliseLiveBridgeEndpointUid(std::string(1025, 'x')).empty());

    Provider provider; Port port;
    provider.endpoints = { { "link", "StudioForge Link", 2, true, { 48000.0 }, true },
                           { "wrong-rate", "Other", 2, true, { 44100.0 }, true },
                           { "speakers", "MacBook Speakers", 2, true, { 48000.0 }, false } };
    LiveBridgeController controller(provider, port);
    controller.setPreferredEndpointUid("link");
    assert(controller.connect(100) && controller.state() == LiveBridgeState::ready && port.connected == "link");
    assert(controller.connect(100) && port.connectCalls == 1);
    controller.poll(101); assert(controller.state() == LiveBridgeState::ready);
    ++port.callbacks; controller.poll(102); assert(controller.state() == LiveBridgeState::active);
    controller.poll(2103); assert(controller.state() == LiveBridgeState::error && !port.open);

    // A device disappearing is different from a stalled callback and must
    // immediately invalidate the route.
    assert(controller.connect(2200));
    ++port.callbacks; controller.poll(2201); assert(controller.state() == LiveBridgeState::active);
    port.open = false; controller.poll(2202);
    assert(controller.state() == LiveBridgeState::error);

    controller.setPreferredEndpointUid("missing"); controller.setFallbackEndpointUid("wrong-rate");
    assert(!controller.connect(300) && controller.state() == LiveBridgeState::error);

    controller.setPreferredEndpointUid("wrong-rate"); controller.setFallbackEndpointUid({});
    assert(!controller.connect(350) && controller.state() == LiveBridgeState::error);

    // A manually named physical output is never accepted as a LIVE endpoint.
    controller.setPreferredEndpointUid("speakers");
    assert(!controller.connect(375) && controller.state() == LiveBridgeState::error);

    controller.setFallbackEndpointUid("link");
    assert(controller.connect(400)); controller.disconnect(); controller.disconnect();
    assert(controller.state() == LiveBridgeState::off && !port.open);
    provider.failure = "no Core Audio devices";
    assert(!controller.connect(500) && controller.state() == LiveBridgeState::error);
    provider.failure.clear(); port.reject = true;
    assert(!controller.connect(600) && controller.state() == LiveBridgeState::error);
    return true;
}
