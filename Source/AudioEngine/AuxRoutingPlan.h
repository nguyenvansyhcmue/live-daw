#pragma once

#include "../Models/ProjectIdentifiers.h"
#include <array>
#include <algorithm>
#include <cstddef>
#include <limits>

// Builds a bounded, allocation-free signal-flow plan. An invalid output ID
// means the stereo output; valid IDs must identify another bus in the plan.
template <size_t Capacity>
struct AuxRoutingPlan
{
    struct Bus { BusId id; BusId output; int latency = 0; bool hasDirectInput = false; };
    std::array<size_t, Capacity> order {};
    std::array<int, Capacity> directInputDelay {};
    std::array<int, Capacity> outputDelay {};
    int masterDirectDelay = 0;

    bool build(const std::array<Bus, Capacity>& buses, size_t count) noexcept
    {
        *this = {};
        if (count > Capacity) return false;
        std::array<int, Capacity> target {};
        std::array<int, Capacity> indegree {};
        std::array<int, Capacity> arrival {};
        std::array<int, Capacity> completion {};
        std::array<bool, Capacity> processed {};
        std::array<bool, Capacity> active {};
        target.fill(-1);
        for (size_t i = 0; i < count; ++i)
        {
            if (! buses[i].id.isValid() || buses[i].latency < 0) return false;
            active[i] = buses[i].hasDirectInput;
            for (size_t j = 0; j < i; ++j)
                if (buses[i].id == buses[j].id) return false;
            if (! buses[i].output.isValid()) continue;
            for (size_t j = 0; j < count; ++j)
                if (buses[j].id == buses[i].output) { target[i] = static_cast<int>(j); break; }
            if (target[i] < 0 || target[i] == static_cast<int>(i)) return false;
            ++indegree[static_cast<size_t>(target[i])];
        }
        for (size_t position = 0; position < count; ++position)
        {
            size_t current = count;
            for (size_t i = 0; i < count; ++i)
                if (! processed[i] && indegree[i] == 0) { current = i; break; }
            if (current == count) return false;
            order[position] = current;
            processed[current] = true;
            directInputDelay[current] = buses[current].hasDirectInput ? arrival[current] : 0;
            if (active[current] && buses[current].latency > std::numeric_limits<int>::max() - arrival[current]) return false;
            completion[current] = active[current] ? arrival[current] + buses[current].latency : 0;
            if (target[current] >= 0)
            {
                const auto next = static_cast<size_t>(target[current]);
                if (active[current])
                {
                    arrival[next] = std::max(arrival[next], completion[current]);
                    active[next] = true;
                }
                --indegree[next];
            }
            else if (active[current]) masterDirectDelay = std::max(masterDirectDelay, completion[current]);
        }
        for (size_t i = 0; i < count; ++i)
            if (active[i]) outputDelay[i] = (target[i] >= 0 ? arrival[static_cast<size_t>(target[i])] : masterDirectDelay) - completion[i];
        return true;
    }
};
