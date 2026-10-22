#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace studioforge::link
{
using EndpointId = std::uint64_t; // Caller-owned, nonzero and persisted across sessions.
enum class EndpointKind { source, bus, destination };
struct Endpoint { EndpointId id {}; EndpointKind kind {}; };
struct Route
{
    EndpointId source {}, destination {};
    std::array<unsigned, 2> channelMap { 0, 1 }; // destination L/R -> source channel
    float gain = 1.0f;
    bool muted = false;
};

// Control-thread data. IDs are supplied by the owner; no OS device identity is assumed.
struct RoutingConfig
{
    std::vector<Endpoint> endpoints;
    std::vector<Route> routes;
    bool addRoute(Route route);
    bool removeRoute(EndpointId source, EndpointId destination);
    [[nodiscard]] bool validate(std::string& error) const;
    [[nodiscard]] std::string serialize() const;
    static bool deserialize(const std::string& text, RoutingConfig& result, std::string& error);
};

// Non-owning planar stereo blocks. frames declares each block's actual capacity.
struct InputBlock { EndpointId id {}; const float* left {}; const float* right {}; std::size_t frames {}; };
struct OutputBlock { EndpointId id {}; float* left {}; float* right {}; std::size_t frames {}; };

// Exactly one control publisher and one non-concurrent audio consumer. Construct,
// prepare and destroy only when the consumer is stopped. publish() is control-
// thread-only; process() is audio-thread-only. Arrays must be non-null when
// their counts are nonzero; buffers must not alias and must hold frames samples.
class RoutingCore final
{
    static_assert(std::atomic<int>::is_always_lock_free && std::atomic<bool>::is_always_lock_free,
                  "Routing publication requires lock-free atomic operations");
public:
    RoutingCore(std::size_t maxEndpoints, std::size_t maxRoutes, std::size_t maxFrames);
    bool publish(const RoutingConfig& config, std::string& error);
    // Clears every supplied output up to min(output.frames, frames); returns
    // false if the requested frame count exceeds the prepared bound.
    bool process(const InputBlock* inputs, std::size_t inputCount,
                 OutputBlock* outputs, std::size_t outputCount, std::size_t frames) noexcept;

private:
    struct CompiledRoute { std::size_t from {}, to {}; std::array<unsigned, 2> map {}; float gain {}; bool muted {}; };
    struct Slot
    {
        std::atomic<bool> occupied { false };
        std::vector<Endpoint> endpoints;
        std::vector<CompiledRoute> routes;
        std::vector<std::size_t> order;
    };
    const std::size_t endpointLimit, routeLimit, frameLimit;
    std::array<Slot, 3> slots;
    std::atomic<int> pending { -1 };
    int active = -1;
    std::vector<float> scratch;
};
}
