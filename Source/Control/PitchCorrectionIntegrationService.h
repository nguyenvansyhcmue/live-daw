#pragma once

#include "StudioForgeControlBridge.h"
#include "VibeAutotuneAdapter.h"
#include "../Plugins/PluginHostService.h"

#include <algorithm>
#include <optional>
#include <vector>

enum class PitchCorrectionIntegrationState : uint8_t
{
    ready, pluginNotScanned, pluginNotInstalled, pluginNotInserted, routeInvalid, parameterMappingInvalid, wrongPluginInSlot
};

class PitchCorrectionIntegrationService final
{
public:
    struct Product
    {
        juce::String name;
        juce::String identifier;
        juce::String format;
    };

    struct AppliedTarget
    {
        TrackId track;
        juce::String trackName;
        int fxSlot = -1;
        juce::String pluginName;
        juce::String pluginIdentifier;
        juce::String rootParameter;
        juce::String scaleParameter;
        bool succeeded = false;
        juce::String error;
    };

    struct ApplyAllResult
    {
        std::vector<AppliedTarget> targets;
        juce::String error;
        int successCount() const noexcept
        {
            return static_cast<int>(std::count_if(targets.begin(), targets.end(),
                [] (const auto& target) { return target.succeeded; }));
        }
    };

    struct Status
    {
        PitchCorrectionIntegrationState state = PitchCorrectionIntegrationState::pluginNotScanned;
        juce::String message;
        juce::String pluginIdentifier;
        juce::String format;
        juce::String rootParameter;
        juce::String scaleParameter;
        bool ready() const noexcept { return state == PitchCorrectionIntegrationState::ready; }
    };

    PitchCorrectionIntegrationService(TrackDataModel&, PluginHostService&, StudioForgeControlBridge&);
    std::vector<Product> getCompatibleProducts() const;
    Status validate() const;
    Status ensurePitchCorrectionForVocalLive();
    Status ensureVibeAutotuneForVocalLive() { return ensurePitchCorrectionForVocalLive(); }
    StudioForgeControlBridge::Result applyKey(ControlTarget, const MusicalKey&);
    ApplyAllResult applyKeyToAllCompatibleInstances(const MusicalKey&);

private:
    static bool isCompatible(const juce::PluginDescription&) noexcept;
    std::vector<juce::PluginDescription> findCompatiblePlugins() const;
    Status validateRoute(const ControlRoute&) const;

    TrackDataModel& model;
    PluginHostService& host;
    StudioForgeControlBridge& bridge;
};
