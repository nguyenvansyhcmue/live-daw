#include "PitchCorrectionIntegrationService.h"

#include "../Models/TrackDataModel.h"

#include <algorithm>

namespace
{
juce::String normalized(juce::String text)
{
    return text.toLowerCase().retainCharacters("abcdefghijklmnopqrstuvwxyz0123456789");
}

juce::File bundledVibeAutotune()
{
    const auto application = juce::File::getSpecialLocation(juce::File::currentApplicationFile);
    return application.getChildFile("Contents")
        .getChildFile("Resources").getChildFile("PlugIns").getChildFile("VST3")
        .getChildFile("VibeAutotune.vst3");
}

juce::String stateMessage(PitchCorrectionIntegrationState state)
{
    switch (state)
    {
        case PitchCorrectionIntegrationState::ready: return "Pitch correction is ready";
        case PitchCorrectionIntegrationState::pluginNotScanned: return "Plug-in registry is empty. Scan plug-ins first.";
        case PitchCorrectionIntegrationState::pluginNotInstalled: return "No supported Auto-Tune, VibeAutotune, or Waves Tune Real-Time plug-in was found.";
        case PitchCorrectionIntegrationState::pluginNotInserted: return "Insert and load a supported pitch-correction plug-in in the vocal FX rack.";
        case PitchCorrectionIntegrationState::routeInvalid: return "Vocal pitch-correction route is invalid.";
        case PitchCorrectionIntegrationState::parameterMappingInvalid: return "Pitch-correction key/scale parameter mapping is invalid.";
        case PitchCorrectionIntegrationState::wrongPluginInSlot: return "Configured vocal FX slot contains an unsupported plug-in.";
    }
    return {};
}

int productPriority(const juce::PluginDescription& plugin)
{
    const auto value = normalized(plugin.name);
    if (value.contains("autotunepro")) return 10;
    if (value.contains("autotuneadvanced")) return 20;
    if (value == "autotune" || value.startsWith("autotune20")) return 30;
    if (value.contains("autotuneartist")) return 40;
    if (value.contains("autotunehybrid")) return 50;
    if (value.contains("autotuneefx")) return 60;
    if (value.contains("autotuneaccess")) return 70;
    if (value.contains("wavestunerealtime") || value.contains("wavestunert")) return 80;
    return 100;
}

const ControlRoute* routeForSlot(const TrackDataModel& model, TrackId track, int slot)
{
    const auto& profile = model.getControlRoutingProfile();
    const auto found = std::find_if(profile.routes.begin(), profile.routes.end(), [track, slot] (const auto& route)
    {
        return route.effect == ControlEffect::pitchCorrection && route.track == track && route.fxSlot == slot;
    });
    return found == profile.routes.end() ? nullptr : &*found;
}
}

PitchCorrectionIntegrationService::PitchCorrectionIntegrationService(TrackDataModel& modelIn,
                                                                     PluginHostService& hostIn,
                                                                     StudioForgeControlBridge& bridgeIn)
    : model(modelIn), host(hostIn), bridge(bridgeIn) {}

bool PitchCorrectionIntegrationService::isCompatible(const juce::PluginDescription& description) noexcept
{
    return VibeAutotuneAdapter::supportsProduct(description.name, description.createIdentifierString());
}

std::vector<juce::PluginDescription> PitchCorrectionIntegrationService::findCompatiblePlugins() const
{
    const auto plugins = host.getKnownPlugins();
    const auto canonicalVibe = bundledVibeAutotune();
    const auto canonicalPath = canonicalVibe.getFullPathName();
    const auto canonicalExists = canonicalVibe.isDirectory();
    std::vector<juce::PluginDescription> matches;
    juce::StringArray identifiers;

    for (const auto& plugin : plugins)
    {
        if (! isCompatible(plugin)) continue;
        const auto vibe = normalized(plugin.name) == "vibeautotune"
                       || normalized(plugin.createIdentifierString()).contains("vibeautotune");
        if (vibe && canonicalExists && plugin.pluginFormatName.equalsIgnoreCase("VST3")
            && juce::File { plugin.fileOrIdentifier }.getFullPathName() != canonicalPath)
            continue;
        const auto identifier = plugin.createIdentifierString();
        if (identifiers.contains(identifier)) continue;
        identifiers.add(identifier);
        matches.push_back(plugin);
    }

    std::stable_sort(matches.begin(), matches.end(), [] (const auto& left, const auto& right)
    {
        const auto leftPriority = productPriority(left);
        const auto rightPriority = productPriority(right);
        if (leftPriority != rightPriority) return leftPriority < rightPriority;
        if (left.pluginFormatName != right.pluginFormatName)
            return left.pluginFormatName.equalsIgnoreCase("VST3");
        return left.name.compareIgnoreCase(right.name) < 0;
    });
    return matches;
}

std::vector<PitchCorrectionIntegrationService::Product>
PitchCorrectionIntegrationService::getCompatibleProducts() const
{
    std::vector<Product> products;
    for (const auto& plugin : findCompatiblePlugins())
        products.push_back({ plugin.name, plugin.createIdentifierString(), plugin.pluginFormatName });
    return products;
}

PitchCorrectionIntegrationService::Status
PitchCorrectionIntegrationService::validateRoute(const ControlRoute& route) const
{
    if (! route.track.isValid() || route.fxSlot < 0
        || route.fxSlot >= static_cast<int>(TrackDataModel::maxFxSlots))
        return { PitchCorrectionIntegrationState::routeInvalid,
                 stateMessage(PitchCorrectionIntegrationState::routeInvalid) };
    const auto track = model.getTrackIndex(route.track);
    if (track < 0)
        return { PitchCorrectionIntegrationState::routeInvalid, "Configured vocal track is missing." };
    const auto* rack = model.getFxRackSnapshot(static_cast<size_t>(track));
    const auto* processor = rack != nullptr
        ? rack->processors[static_cast<size_t>(route.fxSlot)].get() : nullptr;
    if (processor == nullptr)
        return { PitchCorrectionIntegrationState::pluginNotInserted,
                 stateMessage(PitchCorrectionIntegrationState::pluginNotInserted) };
    if (! VibeAutotuneAdapter::supportsProduct(processor->getName(), processor->getPersistentIdentifier()))
        return { PitchCorrectionIntegrationState::wrongPluginInSlot,
                 stateMessage(PitchCorrectionIntegrationState::wrongPluginInSlot) };
    if (route.expectedPluginIdentifier.isNotEmpty()
        && processor->getPersistentIdentifier() != route.expectedPluginIdentifier)
        return { PitchCorrectionIntegrationState::wrongPluginInSlot,
                 "The selected pitch-correction plug-in instance changed." };
    const auto mapping = VibeAutotuneAdapter {}.resolve(*processor, route.parameterIdentifier,
                                                        route.secondaryParameterIdentifier);
    if (! mapping.succeeded)
        return { PitchCorrectionIntegrationState::parameterMappingInvalid, mapping.error };
    return { PitchCorrectionIntegrationState::ready, processor->getName() + " is ready",
             processor->getPersistentIdentifier(), {}, mapping.mapping.root, mapping.mapping.scale };
}

PitchCorrectionIntegrationService::Status PitchCorrectionIntegrationService::validate() const
{
    auto routeCount = 0;
    Status lastReady;
    for (const auto& route : model.getControlRoutingProfile().routes)
    {
        if (route.effect != ControlEffect::pitchCorrection
            || (route.target != ControlTarget::mic1 && route.target != ControlTarget::mic2))
            continue;
        ++routeCount;
        const auto status = validateRoute(route);
        if (! status.ready()) return status;
        lastReady = status;
    }
    if (routeCount == 0)
        return { PitchCorrectionIntegrationState::routeInvalid,
                 "No vocal pitch-correction route is configured." };
    return lastReady;
}

PitchCorrectionIntegrationService::Status
PitchCorrectionIntegrationService::ensurePitchCorrectionForVocalLive()
{
    auto profile = model.getControlRoutingProfile();
    auto routeCount = 0;
    for (auto& route : profile.routes)
    {
        if (route.effect != ControlEffect::pitchCorrection
            || (route.target != ControlTarget::mic1 && route.target != ControlTarget::mic2))
            continue;
        ++routeCount;
        const auto track = model.getTrackIndex(route.track);
        if (track < 0)
            return { PitchCorrectionIntegrationState::routeInvalid, "Configured vocal track is missing." };
        if (route.fxSlot < 0 || route.fxSlot >= static_cast<int>(TrackDataModel::maxFxSlots))
            return { PitchCorrectionIntegrationState::routeInvalid,
                     stateMessage(PitchCorrectionIntegrationState::routeInvalid) };

        const auto* rack = model.getFxRackSnapshot(static_cast<size_t>(track));
        auto existing = rack != nullptr ? rack->processors[static_cast<size_t>(route.fxSlot)] : nullptr;
        if (existing != nullptr
            && ! VibeAutotuneAdapter::supportsProduct(existing->getName(), existing->getPersistentIdentifier()))
            return { PitchCorrectionIntegrationState::wrongPluginInSlot,
                     stateMessage(PitchCorrectionIntegrationState::wrongPluginInSlot) };

        if (existing == nullptr)
        {
            // Detection must never instantiate a product merely because it is
            // installed. The user owns the FX rack; mapping becomes active
            // only after an actual processor instance has been loaded.
            return { PitchCorrectionIntegrationState::pluginNotInserted,
                     stateMessage(PitchCorrectionIntegrationState::pluginNotInserted) };
        }

        const auto mapping = VibeAutotuneAdapter {}.resolve(*existing, route.parameterIdentifier,
                                                            route.secondaryParameterIdentifier);
        if (! mapping.succeeded)
            return { PitchCorrectionIntegrationState::parameterMappingInvalid, mapping.error };
        route.expectedPluginIdentifier = existing->getPersistentIdentifier();
        route.parameterIdentifier = mapping.mapping.root;
        route.secondaryParameterIdentifier = mapping.mapping.scale;
    }

    if (routeCount == 0)
        return { PitchCorrectionIntegrationState::routeInvalid,
                 "Create or configure a Vocal track before preparing pitch correction." };
    if (const auto result = model.setControlRoutingProfile(std::move(profile)); result.failed())
        return { PitchCorrectionIntegrationState::routeInvalid, result.getErrorMessage() };
    return validate();
}

StudioForgeControlBridge::Result
PitchCorrectionIntegrationService::applyKey(ControlTarget target, const MusicalKey& key)
{
    const auto status = validate();
    if (! status.ready())
    {
        StudioForgeControlBridge::Result result;
        result.error = status.message;
        return result;
    }
    return bridge.apply(ControlCommand::keySignatureFor(target, key.rootNote(), key.isMinor()));
}

PitchCorrectionIntegrationService::ApplyAllResult
PitchCorrectionIntegrationService::applyKeyToAllCompatibleInstances(const MusicalKey& key)
{
    ApplyAllResult output;
    // Intentionally scan the live rack rather than the installed-product
    // catalog. An installed plug-in is not a target until the user inserts it
    // into this project.
    for (size_t trackIndex = 0; trackIndex < model.getTrackCount(); ++trackIndex)
    {
        const auto& track = model.getTrack(trackIndex);
        const auto* rack = model.getFxRackSnapshot(trackIndex);
        if (rack == nullptr) continue;
        for (size_t slot = 0; slot < TrackDataModel::maxFxSlots; ++slot)
        {
            const auto& processor = rack->processors[slot];
            if (processor == nullptr
                || ! VibeAutotuneAdapter::supportsProduct(processor->getName(),
                                                           processor->getPersistentIdentifier()))
                continue;
            const auto* route = routeForSlot(model, track.id, static_cast<int>(slot));
            const auto configuredRoot = route != nullptr ? route->parameterIdentifier : juce::String {};
            const auto configuredScale = route != nullptr ? route->secondaryParameterIdentifier : juce::String {};
            const auto applied = VibeAutotuneAdapter {}.apply(*processor, key, configuredRoot, configuredScale);
            output.targets.push_back({ track.id, track.name, static_cast<int>(slot), processor->getName(),
                                       processor->getPersistentIdentifier(), applied.mapping.root,
                                       applied.mapping.scale, applied.succeeded, applied.error });
        }
    }
    if (output.successCount() == 0)
        output.error = output.targets.empty()
            ? "No loaded Auto-Tune, VibeAutotune, or Waves Tune Real-Time instance was found in this project."
            : "Loaded pitch-correction instances rejected the requested key/scale.";
    return output;
}
