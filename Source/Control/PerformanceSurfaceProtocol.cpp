#include "PerformanceSurfaceProtocol.h"
#include "../AudioEngine/AudioEngine.h"
#include "PitchCorrectionIntegrationService.h"

#include <algorithm>
#include <cmath>
#include <map>

namespace
{
// The bridge is newline-delimited JSON (JSON Lines): a response must never
// contain a formatting newline, otherwise the companion reads only "{" and
// reports a misleading connection/JSON error.
juce::String toWireJson(const juce::var& value)
{
    return juce::JSON::toString(value, true);
}

juce::var makeObject()
{
    return juce::var(new juce::DynamicObject());
}

juce::DynamicObject* objectFor(juce::var& value)
{
    return value.getDynamicObject();
}

juce::String stringProperty(const juce::DynamicObject& object, const char* name)
{
    return object.getProperty(name).toString();
}

bool readInteger(const juce::DynamicObject& object, const char* name, int& value)
{
    const auto source = object.getProperty(name);
    if (! source.isInt() && ! source.isInt64()) return false;
    value = static_cast<int>(source);
    return true;
}

bool readRevision(const juce::DynamicObject& object, uint64_t& value)
{
    const auto source = object.getProperty("projectRevision").toString().trim();
    if (source.isEmpty()) return false;
    try { value = static_cast<uint64_t>(source.getLargeIntValue()); }
    catch (...) { return false; }
    return true;
}

bool readNormalisedValue(const juce::DynamicObject& object, const char* name, float& value)
{
    const auto source = object.getProperty(name);
    if (! source.isInt() && ! source.isInt64() && ! source.isDouble()) return false;
    value = static_cast<float>(source);
    return std::isfinite(value) && value >= 0.0f && value <= 1.0f;
}

struct EqBandParameterSet
{
    const PerformanceMacroService::ParameterOption* used = nullptr;
    const PerformanceMacroService::ParameterOption* enabled = nullptr;
    const PerformanceMacroService::ParameterOption* frequency = nullptr;
    const PerformanceMacroService::ParameterOption* gain = nullptr;
    const PerformanceMacroService::ParameterOption* q = nullptr;
    const PerformanceMacroService::ParameterOption* shape = nullptr;
    const PerformanceMacroService::ParameterOption* dynamicRange = nullptr;
};

struct MasterPluginTarget
{
    std::shared_ptr<AudioEffectProcessor> processor;
    juce::String identifier;
    bool bypassed = false;
};

MasterPluginTarget masterPluginTarget(AudioEngine* engine, int slot)
{
    MasterPluginTarget target;
    if (engine == nullptr || slot < 0 || slot >= static_cast<int>(TrackDataModel::maxFxSlots))
        return target;
    const auto* rack = engine->getMasterFxRackSnapshot();
    if (rack == nullptr || rack->processors[static_cast<size_t>(slot)] == nullptr)
        return target;
    target.processor = rack->processors[static_cast<size_t>(slot)];
    target.bypassed = rack->bypass[static_cast<size_t>(slot)];
    const auto persistent = target.processor->getPersistentIdentifier();
    target.identifier = "master:" + juce::String(slot) + ":"
        + (persistent.isNotEmpty() ? persistent : target.processor->getName());
    return target;
}

MasterPluginTarget trackPluginTarget(TrackDataModel& model, TrackId track, int slot)
{
    MasterPluginTarget target;
    const auto trackIndex = model.getTrackIndex(track);
    if (trackIndex < 0 || slot < 0 || slot >= static_cast<int>(TrackDataModel::maxFxSlots))
        return target;
    const auto* rack = model.getFxRackSnapshot(static_cast<size_t>(trackIndex));
    if (rack == nullptr || rack->processors[static_cast<size_t>(slot)] == nullptr)
        return target;
    target.processor = rack->processors[static_cast<size_t>(slot)];
    target.bypassed = rack->bypass[static_cast<size_t>(slot)];
    const auto persistent = target.processor->getPersistentIdentifier();
    target.identifier = "track:" + juce::String(track.value) + ":" + juce::String(slot) + ":"
        + (persistent.isNotEmpty() ? persistent : target.processor->getName());
    return target;
}

bool parseTrackTarget(const juce::String& text, TrackId& track)
{
    if (! text.startsWith("track:")) return false;
    track = TrackId { static_cast<uint64_t>(text.fromFirstOccurrenceOf(":", false, false).getLargeIntValue()) };
    return track.isValid();
}

std::vector<PerformanceMacroService::ParameterOption> parameterOptionsFor(
    const std::shared_ptr<AudioEffectProcessor>& processor)
{
    std::vector<PerformanceMacroService::ParameterOption> options;
    if (processor == nullptr) return options;
    for (const auto& ranked : PluginSemanticMapper::rankParameters(
             processor->getName(), processor->getParameterDescriptors()))
    {
        const auto& descriptor = ranked.descriptor;
        options.push_back({ descriptor.identifier, descriptor.name, descriptor.groupPath, descriptor.unit,
                            descriptor.currentValueText, descriptor.currentNormalised,
                            descriptor.defaultNormalised, descriptor.automatable,
                            descriptor.readOnly, descriptor.stableIdentifier,
                            PluginSemanticMapper::categoryName(ranked.category), ranked.role,
                            ranked.importance, ranked.recommended, ranked.safeForMacro,
                            ranked.dangerLevel, ranked.reason });
    }
    return options;
}

int eqBandIndex(const juce::String& name)
{
    if (! name.startsWithIgnoreCase("Band ")) return 0;
    const auto tail = name.substring(5);
    const auto number = tail.upToFirstOccurrenceOf(" ", false, false).getIntValue();
    return number > 0 ? number : 0;
}

void addParameterField(juce::DynamicObject& destination, const char* name,
                       const PerformanceMacroService::ParameterOption* parameter)
{
    if (parameter == nullptr) return;
    auto value = makeObject();
    auto* object = objectFor(value);
    object->setProperty("parameterId", parameter->identifier);
    object->setProperty("displayValue", parameter->valueText);
    object->setProperty("normalizedValue", parameter->value);
    object->setProperty("automatable", parameter->automatable);
    object->setProperty("readOnly", parameter->readOnly);
    destination.setProperty(name, std::move(value));
}

bool isEditable(const PerformanceMacroService::ParameterOption* parameter)
{
    return parameter != nullptr && parameter->stableIdentifier && parameter->automatable && ! parameter->readOnly;
}

bool isVerifiedFabFilterProQ(const juce::String& name)
{
    // AU/VST3 hosts do not agree on whether the vendor is included in the
    // display name ("Pro-Q 3" vs "FabFilter Pro-Q 3").  Keep this whitelist
    // deliberately narrow because the normalised parameter model below is a
    // measured Pro-Q contract, not a generic-EQ guess.
    const auto compact = name.trim().toLowerCase();
    return compact.contains("pro-q 2") || compact.contains("pro-q 3")
        || compact.contains("pro-q 4");
}
}

PerformanceSurfaceProtocol::PerformanceSurfaceProtocol(TrackDataModel& model,
                                                       PerformanceMacroService& macros,
                                                       juce::String sessionToken,
                                                       AudioEngine* engine,
                                                       PitchCorrectionIntegrationService* pitchCorrectionIn)
    : dataModel(model), macroService(macros), token(std::move(sessionToken)), audioEngine(engine),
      pitchCorrection(pitchCorrectionIn)
{
}

juce::var PerformanceSurfaceProtocol::snapshotToVar(const PerformanceMacroService::Snapshot& snapshot)
{
    auto value = makeObject();
    auto* object = objectFor(value);
    object->setProperty("macroId", static_cast<int>(snapshot.macroIndex));
    object->setProperty("macroName", snapshot.displayName);
    object->setProperty("value", snapshot.value);
    object->setProperty("state", static_cast<int>(snapshot.state));
    object->setProperty("busId", juce::String(snapshot.bus.value));
    object->setProperty("busName", snapshot.busName);
    object->setProperty("targetId", snapshot.targetId);
    object->setProperty("targetScope", snapshot.targetScope == PerformanceMacroService::TargetScope::master ? "master"
                                      : (snapshot.targetScope == PerformanceMacroService::TargetScope::track ? "track" : "bus"));
    object->setProperty("targetName", snapshot.busName);
    object->setProperty("pluginSlot", snapshot.pluginSlot);
    object->setProperty("pluginInstanceId", snapshot.pluginIdentifier);
    object->setProperty("pluginName", snapshot.pluginName);
    object->setProperty("confidence", snapshot.mapping.confidence);
    object->setProperty("needsReview", snapshot.mapping.needsReview);

    juce::Array<juce::var> targets;
    for (size_t targetIndex = 0; targetIndex < snapshot.targets.size(); ++targetIndex)
    {
        const auto& target = snapshot.targets[targetIndex];
        auto targetValue = makeObject();
        auto* targetObject = objectFor(targetValue);
        targetObject->setProperty("parameterId", target.parameterIdentifier);
        targetObject->setProperty("name", target.displayName);
        targetObject->setProperty("semantic", static_cast<int>(target.semantic));
        targetObject->setProperty("valueText", target.valueText);
        // A mode profile must be able to restore the exact feel of a macro,
        // not merely rediscover a parameter by display name.  These values
        // come from the DAW-owned persisted mapping and use the same stable
        // parameter identifier validated by applyMacroMapping.
        if (targetIndex < snapshot.mapping.targets.size())
        {
            const auto& mapping = snapshot.mapping.targets[targetIndex];
            targetObject->setProperty("minimum", mapping.minimum);
            targetObject->setProperty("maximum", mapping.maximum);
            targetObject->setProperty("curve", static_cast<int>(mapping.curve));
            targetObject->setProperty("invert", mapping.invert);
            targetObject->setProperty("smoothingMs", mapping.smoothingMs);
        }
        targets.add(std::move(targetValue));
    }
    object->setProperty("targets", std::move(targets));
    return value;
}

juce::String PerformanceSurfaceProtocol::makeStatePayload() const
{
    auto root = makeObject();
    auto* object = objectFor(root);
    object->setProperty("type", "performanceMacroState");
    object->setProperty("projectRevision", juce::String(dataModel.getProjectRevision()));
    object->setProperty("transportPlaying", audioEngine != nullptr && audioEngine->isPlaying());
    juce::Array<juce::var> macros;
    for (size_t index = 0; index < PerformanceMacroService::macroCount; ++index)
        macros.add(snapshotToVar(macroService.getSnapshot(index)));
    object->setProperty("macros", std::move(macros));
    juce::Array<juce::var> buses;
    for (const auto& bus : macroService.getBusOptions())
    {
        auto busValue = makeObject();
        auto* busObject = objectFor(busValue);
        busObject->setProperty("id", juce::String(bus.id.value));
        busObject->setProperty("name", bus.name);
        juce::Array<juce::var> plugins;
        for (const auto& plugin : macroService.getPluginOptions(bus.id))
        {
            auto pluginValue = makeObject();
            auto* pluginObject = objectFor(pluginValue);
            pluginObject->setProperty("slot", plugin.slot);
            pluginObject->setProperty("instanceId", plugin.identifier);
            pluginObject->setProperty("name", plugin.name);
            pluginObject->setProperty("bypassed", plugin.bypassed);
            plugins.add(std::move(pluginValue));
        }
        busObject->setProperty("plugins", std::move(plugins));
        buses.add(std::move(busValue));
    }
    object->setProperty("buses", std::move(buses));
    if (pitchCorrection != nullptr)
    {
        juce::Array<juce::var> products;
        for (const auto& product : pitchCorrection->getCompatibleProducts())
        {
            auto item = makeObject();
            objectFor(item)->setProperty("name", product.name);
            objectFor(item)->setProperty("pluginInstanceId", product.identifier);
            objectFor(item)->setProperty("format", product.format);
            products.add(std::move(item));
        }
        object->setProperty("pitchCorrectionProducts", std::move(products));
    }
    if (audioEngine != nullptr)
    {
        // EQ control targets are deliberately separate from persisted macro
        // buses. Master is a real engine-owned rack, not a synthetic BusId.
        juce::Array<juce::var> eqTargets;
        auto masterTarget = makeObject();
        auto* masterObject = objectFor(masterTarget);
        masterObject->setProperty("id", "master");
        masterObject->setProperty("scope", "master");
        masterObject->setProperty("name", "Master");
        juce::Array<juce::var> masterPlugins;
        for (int slot = 0; slot < static_cast<int>(TrackDataModel::maxFxSlots); ++slot)
        {
            const auto plugin = masterPluginTarget(audioEngine, slot);
            if (plugin.processor == nullptr) continue;
            auto item = makeObject();
            objectFor(item)->setProperty("slot", slot);
            objectFor(item)->setProperty("instanceId", plugin.identifier);
            objectFor(item)->setProperty("name", plugin.processor->getName());
            objectFor(item)->setProperty("bypassed", plugin.bypassed);
            masterPlugins.add(std::move(item));
        }
        masterObject->setProperty("plugins", std::move(masterPlugins));
        eqTargets.add(std::move(masterTarget));
        for (size_t trackIndex = 0; trackIndex < dataModel.getTrackCount(); ++trackIndex)
        {
            const auto& track = dataModel.getTrack(trackIndex);
            if (track.type != TrackType::audio) continue;
            auto target = makeObject();
            objectFor(target)->setProperty("id", "track:" + juce::String(track.id.value));
            objectFor(target)->setProperty("scope", "track");
            objectFor(target)->setProperty("name", track.name);
            juce::Array<juce::var> plugins;
            for (int slot = 0; slot < static_cast<int>(TrackDataModel::maxFxSlots); ++slot)
            {
                const auto plugin = trackPluginTarget(dataModel, track.id, slot);
                if (plugin.processor == nullptr) continue;
                auto item = makeObject();
                objectFor(item)->setProperty("slot", slot);
                objectFor(item)->setProperty("instanceId", plugin.identifier);
                objectFor(item)->setProperty("name", plugin.processor->getName());
                objectFor(item)->setProperty("bypassed", plugin.bypassed);
                plugins.add(std::move(item));
            }
            objectFor(target)->setProperty("plugins", std::move(plugins));
            eqTargets.add(std::move(target));
        }
        for (const auto& bus : macroService.getBusOptions())
        {
            auto target = makeObject();
            objectFor(target)->setProperty("id", juce::String(bus.id.value));
            objectFor(target)->setProperty("scope", "bus");
            objectFor(target)->setProperty("name", bus.name);
            juce::Array<juce::var> plugins;
            for (const auto& plugin : macroService.getPluginOptions(bus.id))
            {
                auto item = makeObject();
                objectFor(item)->setProperty("slot", plugin.slot);
                objectFor(item)->setProperty("instanceId", plugin.identifier);
                objectFor(item)->setProperty("name", plugin.name);
                objectFor(item)->setProperty("bypassed", plugin.bypassed);
                plugins.add(std::move(item));
            }
            objectFor(target)->setProperty("plugins", std::move(plugins));
            eqTargets.add(std::move(target));
        }
        object->setProperty("eqTargets", std::move(eqTargets));

        // Mapping uses the same live rack inventory as the DAW's EQ surface:
        // Master, every audio track/line, then buses.  No cached or guessed
        // plug-in list is maintained in the companion app.
        juce::Array<juce::var> macroTargets;
        const auto addMacroTarget = [&macroTargets, this] (const juce::String& id,
                                                           const juce::String& scope,
                                                           const juce::String& name)
        {
            auto target = makeObject();
            auto* targetObject = objectFor(target);
            targetObject->setProperty("id", id);
            targetObject->setProperty("scope", scope);
            targetObject->setProperty("name", name);
            juce::Array<juce::var> plugins;
            for (const auto& plugin : macroService.getPluginOptions(id))
            {
                auto item = makeObject();
                objectFor(item)->setProperty("slot", plugin.slot);
                objectFor(item)->setProperty("instanceId", plugin.identifier);
                objectFor(item)->setProperty("name", plugin.name);
                objectFor(item)->setProperty("bypassed", plugin.bypassed);
                plugins.add(std::move(item));
            }
            targetObject->setProperty("plugins", std::move(plugins));
            macroTargets.add(std::move(target));
        };
        addMacroTarget("master", "master", "Master");
        for (size_t index = 0; index < dataModel.getTrackCount(); ++index)
        {
            const auto& track = dataModel.getTrack(index);
            if (track.type == TrackType::audio)
                addMacroTarget("track:" + juce::String(track.id.value), "track", track.name);
        }
        for (const auto& bus : macroService.getBusOptions())
            addMacroTarget(juce::String(bus.id.value), "bus", bus.name);
        object->setProperty("macroTargets", std::move(macroTargets));

        object->setProperty("audioAnalysis", makeAudioAnalysisValue());

        juce::Array<juce::var> sources;
        auto master = makeObject();
        objectFor(master)->setProperty("kind", "master");
        objectFor(master)->setProperty("id", "master");
        objectFor(master)->setProperty("name", "Master Post-FX");
        sources.add(std::move(master));
        for (size_t index = 0; index < dataModel.getTrackCount(); ++index)
        {
            const auto& track = dataModel.getTrack(index);
            if (track.type != TrackType::audio) continue;
            auto item = makeObject();
            objectFor(item)->setProperty("kind", "track");
            objectFor(item)->setProperty("id", juce::String(track.id.value));
            objectFor(item)->setProperty("name", track.name + " Post-FX");
            sources.add(std::move(item));
        }
        for (const auto& bus : macroService.getBusOptions())
        {
            auto item = makeObject();
            objectFor(item)->setProperty("kind", "bus");
            objectFor(item)->setProperty("id", juce::String(bus.id.value));
            objectFor(item)->setProperty("name", bus.name + " Post-FX");
            sources.add(std::move(item));
        }
        object->setProperty("analysisSources", std::move(sources));
    }
    return toWireJson(root);
}

juce::String PerformanceSurfaceProtocol::makeError(const juce::String& message) const
{
    auto root = makeObject();
    auto* object = objectFor(root);
    object->setProperty("ok", false);
    object->setProperty("error", message);
    object->setProperty("projectRevision", juce::String(dataModel.getProjectRevision()));
    return toWireJson(root);
}

juce::var PerformanceSurfaceProtocol::makeAudioAnalysisValue() const
{
    auto display = makeObject();
    auto* object = objectFor(display);
    if (audioEngine == nullptr)
    {
        object->setProperty("available", false);
        return display;
    }
    const auto analysis = audioEngine->getLiveDisplayAnalysis();
    const auto detectedKey = audioEngine->getLiveKeyResult();
    const auto source = audioEngine->getLiveAnalysisSourceState();
    object->setProperty("available", true);
    object->setProperty("revision", juce::String(analysis.revision));
    object->setProperty("rms", analysis.rms);
    object->setProperty("sourceKind", source.track.isValid() ? "track" : (source.bus.isValid() ? "bus" : "master"));
    object->setProperty("sourceId", source.track.isValid() ? juce::String(source.track.value)
                                     : (source.bus.isValid() ? juce::String(source.bus.value) : "master"));
    object->setProperty("sourceName", source.name);
    object->setProperty("sourceAvailable", source.available);
    object->setProperty("transportRunning", source.transportRunning);
    object->setProperty("keyRevision", juce::String(detectedKey.revision));
    object->setProperty("keyRoot", detectedKey.root);
    object->setProperty("keyMinor", detectedKey.minor);
    object->setProperty("keyConfidence", detectedKey.confidence);
    juce::Array<juce::var> waveform;
    juce::Array<juce::var> spectrum;
    for (const auto value : analysis.waveform) waveform.add(value);
    for (const auto value : analysis.spectrum) spectrum.add(value);
    object->setProperty("waveform", std::move(waveform));
    object->setProperty("spectrum", std::move(spectrum));
    return display;
}

juce::String PerformanceSurfaceProtocol::makeAudioAnalysisPayload() const
{
    auto root = makeObject();
    auto* object = objectFor(root);
    object->setProperty("ok", audioEngine != nullptr);
    object->setProperty("type", "audioAnalysisFrame");
    object->setProperty("projectRevision", juce::String(dataModel.getProjectRevision()));
    object->setProperty("audioAnalysis", makeAudioAnalysisValue());
    return toWireJson(root);
}

juce::String PerformanceSurfaceProtocol::makeSnapshotPayload(const PerformanceMacroService::Snapshot& snapshot) const
{
    auto root = makeObject();
    auto* object = objectFor(root);
    object->setProperty("ok", true);
    object->setProperty("projectRevision", juce::String(dataModel.getProjectRevision()));
    object->setProperty("macro", snapshotToVar(snapshot));
    return toWireJson(root);
}

bool PerformanceSurfaceProtocol::validateEnvelope(const juce::DynamicObject& request, juce::String& error) const
{
    if (token.isEmpty() || stringProperty(request, "token") != token)
    {
        error = "Control-surface session is not authorised";
        return false;
    }
    uint64_t revision = 0;
    if (! readRevision(request, revision) || revision != dataModel.getProjectRevision())
    {
        error = "Project changed; refresh the control surface before applying a macro";
        return false;
    }
    return true;
}

juce::String PerformanceSurfaceProtocol::handleCommand(const juce::String& requestJson)
{
    const auto parsed = juce::JSON::parse(requestJson);
    const auto* request = parsed.getDynamicObject();
    if (request == nullptr) return makeError("Control-surface command is not valid JSON");

    const auto command = stringProperty(*request, "command");
    // State reads use the session token but deliberately do not require a
    // revision. A newly opened control surface needs an authoritative first
    // snapshot before it can include the revision in a mutating command.
    if (command == "getState")
    {
        if (token.isEmpty() || stringProperty(*request, "token") != token)
            return makeError("Control-surface session is not authorised");
        return makeStatePayload();
    }

    if (command == "getAudioAnalysis")
    {
        if (token.isEmpty() || stringProperty(*request, "token") != token)
            return makeError("Control-surface session is not authorised");
        return makeAudioAnalysisPayload();
    }

    // Transport is session-scoped, not project-content mutation. Requiring a
    // project revision here would make Space stop working during the brief
    // interval after an edit and before the companion's next inventory poll.
    // The random local-session token is still mandatory.
    if (command == "toggleTransport")
    {
        if (token.isEmpty() || stringProperty(*request, "token") != token)
            return makeError("Control-surface session is not authorised");
        if (audioEngine == nullptr)
            return makeError("DAW transport is unavailable");

        audioEngine->setPlaybackState(! audioEngine->isPlaying());
        auto root = makeObject();
        auto* object = objectFor(root);
        object->setProperty("ok", true);
        object->setProperty("type", "transportState");
        object->setProperty("playing", audioEngine->isPlaying());
        object->setProperty("projectRevision", juce::String(dataModel.getProjectRevision()));
        return toWireJson(root);
    }

    if (command == "setAudioAnalysisSource")
    {
        juce::String error;
        if (! validateEnvelope(*request, error)) return makeError(error);
        if (audioEngine == nullptr) return makeError("DAW audio analysis is unavailable");
        const auto kind = stringProperty(*request, "sourceKind");
        if (kind == "master")
            audioEngine->selectLiveAnalysisMaster();
        else if (kind == "bus")
        {
            const BusId bus { static_cast<uint64_t>(stringProperty(*request, "sourceId").getLargeIntValue()) };
            if (! audioEngine->selectLiveAnalysisBus(bus))
                return makeError("The selected analysis bus is unavailable");
        }
        else if (kind == "track")
        {
            const TrackId track { static_cast<uint64_t>(stringProperty(*request, "sourceId").getLargeIntValue()) };
            if (! audioEngine->selectLiveAnalysisTrack(track))
                return makeError("The selected analysis track is unavailable");
        }
        else return makeError("Analysis source is invalid");
        return makeStatePayload();
    }

    if (command == "getPluginParameters" || command == "getRecommendedPluginParameters")
    {
        juce::String error;
        if (! validateEnvelope(*request, error)) return makeError(error);
        int slot = -1;
        const auto busText = stringProperty(*request, "busId").trim();
        const auto isMaster = busText == "master";
        TrackId track;
        const auto isTrack = parseTrackTarget(busText, track);
        const BusId bus { (isMaster || isTrack) ? 0u : static_cast<uint64_t>(busText.getLargeIntValue()) };
        const auto pluginIdentifier = stringProperty(*request, "pluginInstanceId");
        if ((! isMaster && ! isTrack && ! bus.isValid()) || ! readInteger(*request, "pluginSlot", slot) || pluginIdentifier.isEmpty())
            return makeError("Bus or plug-in target is invalid");
        std::vector<PerformanceMacroService::ParameterOption> parameters;
        if (isMaster)
        {
            const auto target = masterPluginTarget(audioEngine, slot);
            if (target.processor == nullptr || target.identifier != pluginIdentifier)
                return makeError(target.processor != nullptr ? "The selected plug-in instance changed"
                                                              : "The selected Master slot is empty");
            parameters = parameterOptionsFor(target.processor);
        }
        else if (isTrack)
        {
            const auto target = trackPluginTarget(dataModel, track, slot);
            if (target.processor == nullptr || target.identifier != pluginIdentifier)
                return makeError(target.processor != nullptr ? "The selected plug-in instance changed"
                                                              : "The selected track slot is empty");
            parameters = parameterOptionsFor(target.processor);
        }
        else
        {
            const auto preview = macroService.preview(bus, slot);
            if (! preview.available || preview.pluginIdentifier != pluginIdentifier)
                return makeError(preview.available ? "The selected plug-in instance changed" : preview.error);
            parameters = macroService.getParameterOptions(bus, slot, pluginIdentifier);
        }
        const auto allParameterCount = static_cast<int>(parameters.size());
        if (command == "getRecommendedPluginParameters")
            parameters.erase(std::remove_if(parameters.begin(), parameters.end(), [] (const auto& parameter)
            {
                return ! parameter.recommended || ! parameter.safeForMacro;
            }), parameters.end());

        // Limit individual replies for large plug-ins (for example Pro-Q 4).
        // Legacy clients that omit pagination retain their original response.
        int offset = 0, limit = static_cast<int>(parameters.size());
        const bool paged = request->hasProperty("offset") || request->hasProperty("limit");
        if (paged && (! readInteger(*request, "offset", offset)
                      || ! readInteger(*request, "limit", limit)
                      || offset < 0 || limit < 1 || limit > 100))
            return makeError("Invalid parameter page");
        const auto total = static_cast<int>(parameters.size());
        if (offset > total) return makeError("Parameter page is out of range");
        auto root = makeObject();
        auto* object = objectFor(root);
        object->setProperty("ok", true);
        object->setProperty("projectRevision", juce::String(dataModel.getProjectRevision()));
        object->setProperty("filter", command == "getRecommendedPluginParameters" ? "recommended" : "all");
        object->setProperty("allParameterCount", allParameterCount);
        juce::Array<juce::var> values;
        for (int index = offset; index < total && index - offset < limit; ++index)
        {
            const auto& parameter = parameters[static_cast<size_t>(index)];
            auto item = makeObject();
            auto* value = objectFor(item);
            value->setProperty("parameterId", parameter.identifier);
            value->setProperty("name", parameter.name);
            value->setProperty("groupPath", parameter.groupPath);
            value->setProperty("unit", parameter.unit);
            value->setProperty("displayValue", parameter.valueText);
            value->setProperty("normalizedValue", parameter.value);
            value->setProperty("defaultNormalized", parameter.defaultValue);
            value->setProperty("automatable", parameter.automatable);
            value->setProperty("readOnly", parameter.readOnly);
            value->setProperty("stableIdentifier", parameter.stableIdentifier);
            value->setProperty("category", parameter.category);
            value->setProperty("role", parameter.role);
            value->setProperty("importance", parameter.importance);
            value->setProperty("recommended", parameter.recommended);
            value->setProperty("safeForMacro", parameter.safeForMacro);
            value->setProperty("dangerLevel", parameter.dangerLevel);
            value->setProperty("reason", parameter.recommendationReason);
            values.add(std::move(item));
        }
        object->setProperty("parameters", std::move(values));
        if (paged)
        {
            const auto next = offset + juce::jmin(limit, total - offset);
            object->setProperty("total", total);
            object->setProperty("nextOffset", next < total ? next : -1);
        }
        return toWireJson(root);
    }

    if (command == "getPluginParameter")
    {
        juce::String error;
        if (! validateEnvelope(*request, error)) return makeError(error);
        int slot = -1;
        const auto busText = stringProperty(*request, "busId").trim();
        const auto isMaster = busText == "master";
        TrackId track;
        const auto isTrack = parseTrackTarget(busText, track);
        const BusId bus { (isMaster || isTrack) ? 0u : static_cast<uint64_t>(busText.getLargeIntValue()) };
        const auto instance = stringProperty(*request, "pluginInstanceId");
        const auto identifier = stringProperty(*request, "parameterId");
        if ((! isMaster && ! isTrack && ! bus.isValid()) || ! readInteger(*request, "pluginSlot", slot)
            || instance.isEmpty() || identifier.isEmpty())
            return makeError("Plug-in parameter target is invalid");
        std::vector<PerformanceMacroService::ParameterOption> options;
        if (isMaster)
        {
            const auto target = masterPluginTarget(audioEngine, slot);
            if (target.processor == nullptr || target.identifier != instance)
                return makeError(target.processor != nullptr ? "The selected plug-in instance changed"
                                                              : "The selected Master slot is empty");
            options = parameterOptionsFor(target.processor);
        }
        else if (isTrack)
        {
            const auto target = trackPluginTarget(dataModel, track, slot);
            if (target.processor == nullptr || target.identifier != instance)
                return makeError(target.processor != nullptr ? "The selected plug-in instance changed"
                                                              : "The selected track slot is empty");
            options = parameterOptionsFor(target.processor);
        }
        else
        {
            const auto preview = macroService.preview(bus, slot);
            if (! preview.available || preview.pluginIdentifier != instance)
                return makeError(preview.available ? "The selected plug-in instance changed" : preview.error);
            options = macroService.getParameterOptions(bus, slot, instance);
        }
        const auto found = std::find_if(options.begin(), options.end(), [&identifier] (const auto& option)
        {
            return option.identifier == identifier;
        });
        if (found == options.end() || ! found->stableIdentifier || ! found->automatable || found->readOnly)
            return makeError("This plug-in parameter is not safely automatable");
        auto root = makeObject();
        auto* object = objectFor(root);
        object->setProperty("ok", true);
        object->setProperty("projectRevision", juce::String(dataModel.getProjectRevision()));
        object->setProperty("parameterId", found->identifier);
        object->setProperty("normalizedValue", found->value);
        object->setProperty("displayValue", found->valueText);
        return toWireJson(root);
    }

    if (command == "getEqSurface")
    {
        juce::String error;
        if (! validateEnvelope(*request, error)) return makeError(error);
        int slot = -1;
        const auto busText = stringProperty(*request, "busId").trim();
        const auto isMaster = busText == "master";
        TrackId track;
        const auto isTrack = parseTrackTarget(busText, track);
        const BusId bus { (isMaster || isTrack) ? 0u : static_cast<uint64_t>(busText.getLargeIntValue()) };
        const auto pluginIdentifier = stringProperty(*request, "pluginInstanceId");
        if ((! isMaster && ! isTrack && ! bus.isValid()) || ! readInteger(*request, "pluginSlot", slot) || pluginIdentifier.isEmpty())
            return makeError("Bus or EQ plug-in target is invalid");

        juce::String targetName, pluginName;
        bool bypassed = false;
        std::vector<PerformanceMacroService::ParameterOption> parameters;
        if (isMaster)
        {
            const auto target = masterPluginTarget(audioEngine, slot);
            if (target.processor == nullptr || target.identifier != pluginIdentifier)
                return makeError(target.processor != nullptr ? "The selected EQ plug-in instance changed"
                                                              : "The selected Master slot is empty");
            targetName = "Master";
            pluginName = target.processor->getName();
            bypassed = target.bypassed;
            parameters = parameterOptionsFor(target.processor);
        }
        else if (isTrack)
        {
            const auto target = trackPluginTarget(dataModel, track, slot);
            if (target.processor == nullptr || target.identifier != pluginIdentifier)
                return makeError(target.processor != nullptr ? "The selected EQ plug-in instance changed"
                                                              : "The selected track slot is empty");
            const auto trackIndex = dataModel.getTrackIndex(track);
            targetName = trackIndex >= 0 ? dataModel.getTrack(static_cast<size_t>(trackIndex)).name : "Track";
            pluginName = target.processor->getName();
            bypassed = target.bypassed;
            parameters = parameterOptionsFor(target.processor);
        }
        else
        {
            const auto preview = macroService.preview(bus, slot);
            if (! preview.available || preview.pluginIdentifier != pluginIdentifier)
                return makeError(preview.available ? "The selected EQ plug-in instance changed" : preview.error);
            targetName = preview.busName;
            pluginName = preview.pluginName;
            bypassed = preview.bypassed;
            parameters = macroService.getParameterOptions(bus, slot, pluginIdentifier);
        }
        std::map<int, EqBandParameterSet> bands;
        for (const auto& parameter : parameters)
        {
            const auto band = eqBandIndex(parameter.name);
            if (band == 0) continue;
            auto& fields = bands[band];
            const auto tail = parameter.name.fromFirstOccurrenceOf(" ", false, false)
                                            .fromFirstOccurrenceOf(" ", false, false);
            if (tail.equalsIgnoreCase("Used")) fields.used = &parameter;
            else if (tail.equalsIgnoreCase("Enabled")) fields.enabled = &parameter;
            else if (tail.equalsIgnoreCase("Frequency")) fields.frequency = &parameter;
            else if (tail.equalsIgnoreCase("Gain")) fields.gain = &parameter;
            else if (tail.equalsIgnoreCase("Q")) fields.q = &parameter;
            else if (tail.equalsIgnoreCase("Shape")) fields.shape = &parameter;
            else if (tail.equalsIgnoreCase("Dynamic Range")) fields.dynamicRange = &parameter;
        }

        int completeBandCount = 0;
        int limitedBandCount = 0;
        juce::Array<juce::var> values;
        for (const auto& [bandIndex, fields] : bands)
        {
            const auto hasCore = isEditable(fields.frequency) && isEditable(fields.gain) && isEditable(fields.q);
            const auto complete = hasCore && isEditable(fields.shape);
            if (complete) ++completeBandCount;
            else if (hasCore || fields.frequency != nullptr) ++limitedBandCount;
            auto item = makeObject();
            auto* object = objectFor(item);
            object->setProperty("bandId", "band:" + juce::String(bandIndex));
            object->setProperty("index", bandIndex);
            object->setProperty("complete", complete);
            addParameterField(*object, "used", fields.used);
            addParameterField(*object, "enabled", fields.enabled);
            addParameterField(*object, "frequency", fields.frequency);
            addParameterField(*object, "gain", fields.gain);
            addParameterField(*object, "q", fields.q);
            addParameterField(*object, "shape", fields.shape);
            addParameterField(*object, "dynamicRange", fields.dynamicRange);
            values.add(std::move(item));
        }

        auto root = makeObject();
        auto* object = objectFor(root);
        object->setProperty("ok", true);
        object->setProperty("type", "eqSurfaceDescriptor");
        object->setProperty("projectRevision", juce::String(dataModel.getProjectRevision()));
        object->setProperty("busId", busText);
        object->setProperty("busName", targetName);
        object->setProperty("targetScope", isMaster ? "master" : (isTrack ? "track" : "bus"));
        object->setProperty("pluginSlot", slot);
        object->setProperty("pluginInstanceId", pluginIdentifier);
        object->setProperty("pluginName", pluginName);
        object->setProperty("bypassed", bypassed);
        // The control bridge does not transport DAW PCM.  Local capture is
        // owned by the companion and must not be advertised as a bus tap.
        object->setProperty("audioTapAvailability", juce::Array<juce::var> {});
        // Name-based grouping exposes candidates but does not establish the
        // plug-in's numeric transfer functions or an exact response curve.
        const auto verifiedProQ = isVerifiedFabFilterProQ(pluginName) && completeBandCount > 0;
        object->setProperty("capability", verifiedProQ ? "eq_interactive"
                                                        : ((completeBandCount > 0 || limitedBandCount > 0)
                                                               ? "eq_limited" : "analyzer_only"));
        if (verifiedProQ)
        {
            auto model = makeObject();
            auto* mapping = objectFor(model);
            mapping->setProperty("family", "fabfilter-pro-q-v2-v4");
            mapping->setProperty("frequencyMinHz", 10.0);
            mapping->setProperty("frequencyMaxHz", 30000.0);
            mapping->setProperty("gainMinDb", -30.0);
            mapping->setProperty("gainMaxDb", 30.0);
            object->setProperty("parameterModel", std::move(model));
        }
        object->setProperty("candidateBandCount", completeBandCount);
        object->setProperty("bands", std::move(values));
        return toWireJson(root);
    }

    if (command == "setEqParameter")
    {
        juce::String error;
        if (! validateEnvelope(*request, error)) return makeError(error);
        int slot = -1;
        float value = 0.0f;
        const auto busText = stringProperty(*request, "busId").trim();
        const auto isMaster = busText == "master";
        TrackId track;
        const auto isTrack = parseTrackTarget(busText, track);
        const BusId bus { (isMaster || isTrack) ? 0u : static_cast<uint64_t>(busText.getLargeIntValue()) };
        const auto pluginIdentifier = stringProperty(*request, "pluginInstanceId");
        const auto parameterIdentifier = stringProperty(*request, "parameterId").trim();
        if ((! isMaster && ! isTrack && ! bus.isValid()) || ! readInteger(*request, "pluginSlot", slot)
            || pluginIdentifier.isEmpty() || parameterIdentifier.isEmpty()
            || ! readNormalisedValue(*request, "value", value))
            return makeError("EQ parameter update is invalid");
        PerformanceMacroService::ParameterWriteResult result;
        if (isMaster)
        {
            const auto target = masterPluginTarget(audioEngine, slot);
            if (target.processor == nullptr || target.identifier != pluginIdentifier)
                return makeError(target.processor != nullptr ? "The selected plug-in instance changed"
                                                              : "The selected Master slot is empty");
            const auto options = parameterOptionsFor(target.processor);
            const auto option = std::find_if(options.begin(), options.end(), [&parameterIdentifier] (const auto& item)
            {
                return item.identifier == parameterIdentifier;
            });
            if (option == options.end() || ! option->stableIdentifier || ! option->automatable || option->readOnly)
                return makeError("This EQ parameter is not safely automatable");
            if (! target.processor->setParameterValue(parameterIdentifier, value))
                return makeError("The EQ plug-in rejected the parameter update");
            const auto refreshed = parameterOptionsFor(target.processor);
            const auto updated = std::find_if(refreshed.begin(), refreshed.end(), [&parameterIdentifier] (const auto& item)
            {
                return item.identifier == parameterIdentifier;
            });
            if (updated == refreshed.end()) return makeError("The EQ parameter disappeared after update");
            result.succeeded = true;
            result.parameter = *updated;
        }
        else if (isTrack)
        {
            const auto target = trackPluginTarget(dataModel, track, slot);
            if (target.processor == nullptr || target.identifier != pluginIdentifier)
                return makeError(target.processor != nullptr ? "The selected plug-in instance changed"
                                                              : "The selected track slot is empty");
            const auto options = parameterOptionsFor(target.processor);
            const auto option = std::find_if(options.begin(), options.end(), [&parameterIdentifier] (const auto& item)
            {
                return item.identifier == parameterIdentifier;
            });
            if (option == options.end() || ! option->stableIdentifier || ! option->automatable || option->readOnly)
                return makeError("This EQ parameter is not safely automatable");
            if (! target.processor->setParameterValue(parameterIdentifier, value))
                return makeError("The EQ plug-in rejected the parameter update");
            const auto refreshed = parameterOptionsFor(target.processor);
            const auto updated = std::find_if(refreshed.begin(), refreshed.end(), [&parameterIdentifier] (const auto& item)
            {
                return item.identifier == parameterIdentifier;
            });
            if (updated == refreshed.end()) return makeError("The EQ parameter disappeared after update");
            result.succeeded = true;
            result.parameter = *updated;
        }
        else
            result = macroService.setParameterValue(bus, slot, pluginIdentifier, parameterIdentifier, value);
        if (! result.succeeded) return makeError(result.error);
        auto root = makeObject();
        auto* object = objectFor(root);
        object->setProperty("ok", true);
        object->setProperty("type", "eqParameterUpdated");
        object->setProperty("projectRevision", juce::String(dataModel.getProjectRevision()));
        object->setProperty("parameterId", result.parameter.identifier);
        object->setProperty("normalizedValue", result.parameter.value);
        object->setProperty("displayValue", result.parameter.valueText);
        return toWireJson(root);
    }

    if (command == "applyDetectedKey")
    {
        juce::String error;
        if (! validateEnvelope(*request, error)) return makeError(error);
        if (pitchCorrection == nullptr)
            return makeError("DAW pitch-correction integration is unavailable");

        float confidence = 0.0f;
        if (! readNormalisedValue(*request, "confidence", confidence))
            return makeError("Detected-key confidence is invalid");
        if (confidence < 0.60f)
            return makeError("Detected-key confidence is too low to update pitch correction");

        const auto key = MusicalKey::parse(stringProperty(*request, "key"),
                                           stringProperty(*request, "scale"));
        if (! key.has_value())
            return makeError("Detected key or scale is invalid");

        // Apply only to compatible instances already inserted in the project.
        // Installed products are inventory, never implicit targets.
        const auto applied = pitchCorrection->applyKeyToAllCompatibleInstances(*key);
        auto root = makeObject();
        auto* object = objectFor(root);
        juce::Array<juce::var> targets;
        juce::StringArray errors;
        for (const auto& result : applied.targets)
        {
            auto target = makeObject();
            auto* targetObject = objectFor(target);
            targetObject->setProperty("trackId", juce::String(result.track.value));
            targetObject->setProperty("trackName", result.trackName);
            targetObject->setProperty("fxSlot", result.fxSlot);
            targetObject->setProperty("pluginName", result.pluginName);
            targetObject->setProperty("pluginInstanceId", result.pluginIdentifier);
            targetObject->setProperty("rootParameter", result.rootParameter);
            targetObject->setProperty("scaleParameter", result.scaleParameter);
            targetObject->setProperty("ok", result.succeeded);
            if (result.error.isNotEmpty())
                targetObject->setProperty("error", result.error);
            targets.add(std::move(target));
            if (! result.succeeded)
                errors.add(result.trackName + " / " + result.pluginName + ": " + result.error);
        }

        object->setProperty("ok", applied.successCount() > 0);
        object->setProperty("type", "detectedKeyApplied");
        object->setProperty("projectRevision", juce::String(dataModel.getProjectRevision()));
        object->setProperty("key", key->rootName());
        object->setProperty("scale", key->scaleName());
        object->setProperty("displayName", key->displayName());
        object->setProperty("confidence", confidence);
        object->setProperty("targets", std::move(targets));
        if (applied.successCount() == 0)
            object->setProperty("error", applied.error.isNotEmpty() ? applied.error
                                                                      : errors.joinIntoString(" • "));
        else if (! errors.isEmpty())
            object->setProperty("warning", errors.joinIntoString(" • "));
        return toWireJson(root);
    }

    juce::String error;
    if (! validateEnvelope(*request, error)) return makeError(error);

    int macroId = -1;
    if (! readInteger(*request, "macroId", macroId) || macroId < 0
        || macroId >= static_cast<int>(PerformanceMacroService::macroCount))
        return makeError("Macro identifier is invalid");

    if (command == "clearMacroMapping")
    {
        const auto result = macroService.clear(static_cast<size_t>(macroId));
        return result.succeeded ? makeSnapshotPayload(result.snapshot) : makeError(result.error);
    }
    if (command == "setMacroValue")
    {
        const auto value = request->getProperty("value");
        if (! value.isDouble() && ! value.isInt()) return makeError("Macro value is invalid");
        const auto result = macroService.setValue(static_cast<size_t>(macroId), static_cast<float>(value));
        return result.succeeded ? makeSnapshotPayload(result.snapshot) : makeError(result.error);
    }

    int pluginSlot = -1;
    auto targetId = stringProperty(*request, "targetId").trim();
    if (targetId.isEmpty()) targetId = stringProperty(*request, "busId").trim();
    if (targetId.isEmpty() || ! readInteger(*request, "pluginSlot", pluginSlot))
        return makeError("DAW target or plug-in slot is invalid");
    const auto preview = macroService.preview(targetId, pluginSlot);
    if (! preview.available) return makeError(preview.error);

    const auto expectedPlugin = stringProperty(*request, "pluginInstanceId");
    if (expectedPlugin.isEmpty() || expectedPlugin != preview.pluginIdentifier)
        return makeError("Plug-in target changed; refresh the mapping panel");

    const auto parameterIdentifier = stringProperty(*request, "parameterId").trim();
    if (command == "applyMacroMapping" && parameterIdentifier.isNotEmpty())
    {
        const auto minimum = static_cast<float>(request->getProperty("minNormalized"));
        const auto maximum = static_cast<float>(request->getProperty("maxNormalized"));
        const auto smoothingMs = static_cast<float>(request->getProperty("smoothingMs"));
        int curve = 0;
        if (! readInteger(*request, "curve", curve) || curve < 0 || curve > 3)
            return makeError("Macro curve is invalid");
        const auto result = macroService.applyParameter(static_cast<size_t>(macroId), targetId, pluginSlot,
                                                        expectedPlugin, parameterIdentifier,
                                                        minimum, maximum,
                                                        static_cast<MacroCurve>(curve),
                                                        static_cast<bool>(request->getProperty("invert")),
                                                        smoothingMs);
        return result.succeeded ? makeSnapshotPayload(result.snapshot) : makeError(result.error);
    }

    if (command == "previewMacroMapping" || command == "requestSmartMapping")
    {
        PerformanceMacroService::Snapshot snapshot;
        snapshot.macroIndex = static_cast<size_t>(macroId);
        snapshot.bus = preview.bus;
        snapshot.track = preview.track;
        snapshot.targetScope = preview.targetScope;
        snapshot.targetId = preview.targetId;
        snapshot.pluginSlot = preview.pluginSlot;
        snapshot.busName = preview.busName;
        snapshot.pluginIdentifier = preview.pluginIdentifier;
        snapshot.pluginName = preview.pluginName;
        snapshot.displayName = preview.proposal.displayName;
        snapshot.mapping = preview.proposal;
        for (const auto& target : preview.proposal.targets)
            snapshot.targets.push_back({ target.parameterIdentifier, target.displayName, target.semantic, {} });
        snapshot.state = preview.bypassed ? PerformanceMacroService::State::bypassed
                                          : (preview.proposal.needsReview ? PerformanceMacroService::State::needsReview
                                                                         : PerformanceMacroService::State::active);
        return makeSnapshotPayload(snapshot);
    }
    if (command == "applyMacroMapping")
    {
        const auto result = macroService.apply(static_cast<size_t>(macroId), targetId, pluginSlot,
                                               static_cast<bool>(request->getProperty("confirmNeedsReview")));
        return result.succeeded ? makeSnapshotPayload(result.snapshot) : makeError(result.error);
    }
    return makeError("Unknown control-surface command");
}
