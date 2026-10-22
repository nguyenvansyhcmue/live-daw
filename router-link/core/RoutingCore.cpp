#include "RoutingCore.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace studioforge::link
{
namespace
{
std::size_t scratchSize(std::size_t endpoints, std::size_t frames)
{
    if (frames != 0 && endpoints > std::numeric_limits<std::size_t>::max() / 2 / frames)
        throw std::length_error("Routing scratch capacity overflow");
    return endpoints * 2 * frames;
}
std::size_t indexOf(const std::vector<Endpoint>& endpoints, EndpointId id)
{
    for (std::size_t i = 0; i < endpoints.size(); ++i) if (endpoints[i].id == id) return i;
    return endpoints.size();
}
bool orderFor(const RoutingConfig& config, std::vector<std::size_t>& order)
{
    std::vector<std::size_t> indegree(config.endpoints.size());
    for (const auto& route : config.routes) ++indegree[indexOf(config.endpoints, route.destination)];
    order.clear();
    for (std::size_t i = 0; i < indegree.size(); ++i) if (indegree[i] == 0) order.push_back(i);
    for (std::size_t i = 0; i < order.size(); ++i)
        for (const auto& route : config.routes)
            if (route.source == config.endpoints[order[i]].id)
            {
                const auto target = indexOf(config.endpoints, route.destination);
                if (--indegree[target] == 0) order.push_back(target);
            }
    return order.size() == config.endpoints.size();
}
}

bool RoutingConfig::addRoute(Route route)
{
    auto candidate = *this;
    candidate.routes.push_back(route);
    std::string error;
    if (! candidate.validate(error)) return false;
    routes.push_back(route);
    return true;
}
bool RoutingConfig::removeRoute(EndpointId source, EndpointId destination)
{
    const auto old = routes.size();
    std::erase_if(routes, [=](const auto& route) { return route.source == source && route.destination == destination; });
    return routes.size() != old;
}
bool RoutingConfig::validate(std::string& error) const
{
    for (std::size_t i = 0; i < endpoints.size(); ++i)
    {
        if (endpoints[i].id == 0 || (endpoints[i].kind != EndpointKind::source && endpoints[i].kind != EndpointKind::bus
                                    && endpoints[i].kind != EndpointKind::destination))
        { error = "Invalid endpoint"; return false; }
        for (std::size_t j = 0; j < i; ++j) if (endpoints[i].id == endpoints[j].id)
        { error = "Duplicate endpoint"; return false; }
    }
    for (std::size_t i = 0; i < routes.size(); ++i)
    {
        const auto& route = routes[i];
        const auto from = indexOf(endpoints, route.source), to = indexOf(endpoints, route.destination);
        if (from == endpoints.size() || to == endpoints.size() || from == to
            || endpoints[from].kind == EndpointKind::destination || endpoints[to].kind == EndpointKind::source
            || route.channelMap[0] > 1 || route.channelMap[1] > 1 || ! std::isfinite(route.gain))
        { error = "Invalid route"; return false; }
        for (std::size_t j = 0; j < i; ++j)
            if (routes[j].source == route.source && routes[j].destination == route.destination)
            { error = "Duplicate route"; return false; }
    }
    std::vector<std::size_t> order;
    if (! orderFor(*this, order)) { error = "Routing cycle"; return false; }
    error.clear();
    return true;
}
std::string RoutingConfig::serialize() const
{
    std::ostringstream out;
    out << "STUDIOFORGE_LINK 1\n" << endpoints.size() << ' ' << routes.size() << '\n';
    for (const auto& e : endpoints) out << e.id << ' ' << static_cast<int>(e.kind) << '\n';
    out << std::setprecision(std::numeric_limits<float>::max_digits10);
    for (const auto& r : routes) out << r.source << ' ' << r.destination << ' ' << r.channelMap[0] << ' '
        << r.channelMap[1] << ' ' << r.gain << ' ' << r.muted << '\n';
    return out.str();
}
bool RoutingConfig::deserialize(const std::string& text, RoutingConfig& result, std::string& error)
{
    std::istringstream in(text);
    std::string magic; int version; std::size_t endpointsCount, routesCount;
    if (!(in >> magic >> version >> endpointsCount >> routesCount) || magic != "STUDIOFORGE_LINK" || version != 1
        || endpointsCount > 4096 || routesCount > 65536) { error = "Invalid configuration header"; return false; }
    RoutingConfig next;
    for (std::size_t i = 0; i < endpointsCount; ++i)
    {
        Endpoint e; int kind;
        if (!(in >> e.id >> kind) || kind < 0 || kind > 2) { error = "Invalid endpoint record"; return false; }
        e.kind = static_cast<EndpointKind>(kind); next.endpoints.push_back(e);
    }
    for (std::size_t i = 0; i < routesCount; ++i)
    {
        Route r; int mute;
        if (!(in >> r.source >> r.destination >> r.channelMap[0] >> r.channelMap[1] >> r.gain >> mute)
            || (mute != 0 && mute != 1)) { error = "Invalid route record"; return false; }
        r.muted = mute != 0; next.routes.push_back(r);
    }
    in >> std::ws;
    if (! in.eof()) { error = "Unexpected configuration data"; return false; }
    if (! next.validate(error)) return false;
    result = std::move(next); return true;
}

RoutingCore::RoutingCore(std::size_t maxEndpoints, std::size_t maxRoutes, std::size_t maxFrames)
    : endpointLimit(maxEndpoints), routeLimit(maxRoutes), frameLimit(maxFrames), scratch(scratchSize(maxEndpoints, maxFrames))
{
    for (auto& slot : slots) { slot.endpoints.reserve(maxEndpoints); slot.routes.reserve(maxRoutes); slot.order.reserve(maxEndpoints); }
}
bool RoutingCore::publish(const RoutingConfig& config, std::string& error)
{
    if (config.endpoints.size() > endpointLimit || config.routes.size() > routeLimit || frameLimit == 0)
    { error = "Configuration exceeds prepared capacity"; return false; }
    if (! config.validate(error)) return false;
    int selected = -1;
    for (int i = 0; i < static_cast<int>(slots.size()); ++i)
    {
        bool expected = false;
        if (slots[static_cast<std::size_t>(i)].occupied.compare_exchange_strong(expected, true, std::memory_order_acquire))
        { selected = i; break; }
    }
    if (selected < 0) { error = "No free configuration slot"; return false; }
    auto& slot = slots[static_cast<std::size_t>(selected)];
    slot.endpoints = config.endpoints; slot.routes.clear();
    for (const auto& route : config.routes)
        slot.routes.push_back({ indexOf(config.endpoints, route.source), indexOf(config.endpoints, route.destination),
                                route.channelMap, route.gain, route.muted });
    orderFor(config, slot.order);
    const auto old = pending.exchange(selected, std::memory_order_acq_rel);
    if (old >= 0) slots[static_cast<std::size_t>(old)].occupied.store(false, std::memory_order_release);
    error.clear(); return true;
}
bool RoutingCore::process(const InputBlock* inputs, std::size_t inputCount,
                          OutputBlock* outputs, std::size_t outputCount, std::size_t frames) noexcept
{
    for (std::size_t i = 0; i < outputCount; ++i)
    {
        const auto count = std::min(frames, outputs[i].frames);
        if (outputs[i].left) std::fill_n(outputs[i].left, count, 0.0f);
        if (outputs[i].right) std::fill_n(outputs[i].right, count, 0.0f);
    }
    if (frames > frameLimit) return false;
    const auto next = pending.exchange(-1, std::memory_order_acq_rel);
    if (next >= 0)
    {
        if (active >= 0) slots[static_cast<std::size_t>(active)].occupied.store(false, std::memory_order_release);
        active = next;
    }
    if (active < 0) return true;
    const auto& slot = slots[static_cast<std::size_t>(active)];
    auto channel = [this](std::size_t index, unsigned c) noexcept { return scratch.data() + (index * 2 + c) * frameLimit; };
    for (std::size_t i = 0; i < slot.endpoints.size(); ++i)
        for (unsigned c = 0; c < 2; ++c) std::fill_n(channel(i, c), frames, 0.0f);
    for (std::size_t i = 0; i < inputCount; ++i)
    {
        const auto index = indexOf(slot.endpoints, inputs[i].id);
        if (index == slot.endpoints.size() || slot.endpoints[index].kind != EndpointKind::source) continue;
        const auto count = std::min(frames, inputs[i].frames);
        if (inputs[i].left) std::copy_n(inputs[i].left, count, channel(index, 0));
        if (inputs[i].right) std::copy_n(inputs[i].right, count, channel(index, 1));
    }
    for (const auto from : slot.order)
        for (const auto& route : slot.routes)
            if (route.from == from && ! route.muted)
                for (unsigned c = 0; c < 2; ++c)
                {
                    const auto* source = channel(from, route.map[c]); auto* dest = channel(route.to, c);
                    for (std::size_t frame = 0; frame < frames; ++frame) dest[frame] += source[frame] * route.gain;
                }
    for (std::size_t i = 0; i < outputCount; ++i)
    {
        const auto index = indexOf(slot.endpoints, outputs[i].id);
        if (index == slot.endpoints.size() || slot.endpoints[index].kind != EndpointKind::destination) continue;
        const auto count = std::min(frames, outputs[i].frames);
        if (outputs[i].left) std::copy_n(channel(index, 0), count, outputs[i].left);
        if (outputs[i].right) std::copy_n(channel(index, 1), count, outputs[i].right);
    }
    return true;
}
}
