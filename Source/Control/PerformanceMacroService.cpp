#include "PerformanceMacroService.h"
#include "../AudioEngine/AudioEngine.h"

#include <algorithm>
#include <cmath>

namespace
{
float applyCurve(float value, MacroCurve curve)
{
    value = juce::jlimit(0.0f, 1.0f, value);
    switch (curve)
    {
        case MacroCurve::logarithmic: return std::sqrt(value);
        case MacroCurve::exponential: return value * value;
        case MacroCurve::sCurve:      return value * value * (3.0f - 2.0f * value);
        case MacroCurve::linear:      break;
    }
    return value;
}

// The companion panel must follow an editor gesture too.  For a one-target
// mapping we can recover the physical macro position from the plug-in's
// current normalised parameter value.  This is deliberately the inverse of
// applyCurve(), so the panel never keeps a separate simulated knob state.
float invertCurve(float value, MacroCurve curve)
{
    value = juce::jlimit(0.0f, 1.0f, value);
    switch (curve)
    {
        case MacroCurve::logarithmic: return value * value;
        case MacroCurve::exponential: return std::sqrt(value);
        case MacroCurve::sCurve:
        {
            // A monotonic binary search is stable at the end stops and avoids
            // a fragile closed-form cubic inverse on the UI/control thread.
            float low = 0.0f, high = 1.0f;
            for (int iteration = 0; iteration < 18; ++iteration)
            {
                const auto middle = (low + high) * 0.5f;
                if (applyCurve(middle, curve) < value) low = middle;
                else high = middle;
            }
            return (low + high) * 0.5f;
        }
        case MacroCurve::linear: break;
    }
    return value;
}

bool parseTrackTarget(const juce::String& targetId, TrackId& track)
{
    if (! targetId.startsWith("track:")) return false;
    track = { static_cast<uint64_t>(targetId.fromFirstOccurrenceOf(":", false, false).getLargeIntValue()) };
    return track.isValid();
}
}

PerformanceMacroService::PerformanceMacroService(TrackDataModel& model, AudioEngine* engine)
    : dataModel(model), audioEngine(engine)
{
    for (size_t index = 0; index < macros.size(); ++index)
        macros[index].macroIndex = index;
    dataModel.addChangeListener(this);
}

PerformanceMacroService::~PerformanceMacroService()
{
    dataModel.removeChangeListener(this);
}

bool PerformanceMacroService::isValidMacroIndex(size_t macroIndex) noexcept
{
    return macroIndex < macroCount;
}

juce::String PerformanceMacroService::identifierFor(BusId bus, int pluginSlot,
                                                     const AudioEffectProcessor& processor)
{
    return identifierFor(juce::String(bus.value), pluginSlot, processor);
}

juce::String PerformanceMacroService::identifierFor(const juce::String& targetId, int pluginSlot,
                                                     const AudioEffectProcessor& processor)
{
    const auto persistent = processor.getPersistentIdentifier();
    // A plug-in format identifier names a type, not an instance. Include the
    // project-owned bus/slot identity so two Pro-Q 3 instances can never be
    // confused. If a user moves the instance its saved mapping becomes review
    // state rather than silently targeting a different plug-in.
    return targetId + ":" + juce::String(pluginSlot) + ":"
           + (persistent.isNotEmpty() ? persistent : processor.getName());
}

std::vector<PerformanceMacroService::BusOption> PerformanceMacroService::getBusOptions() const
{
    std::vector<BusOption> options;
    const auto& buses = dataModel.getBuses();
    options.reserve(buses.size());
    for (const auto& bus : buses)
        options.push_back({ bus.id, bus.name });
    return options;
}

std::vector<PerformanceMacroService::PluginOption> PerformanceMacroService::getPluginOptions(BusId bus) const
{
    return getPluginOptions(juce::String(bus.value));
}

std::vector<PerformanceMacroService::PluginOption> PerformanceMacroService::getPluginOptions(
    const juce::String& targetId) const
{
    std::vector<PluginOption> options;
    const TrackDataModel::FxRackSnapshot* rack = nullptr;
    TrackId track;
    if (targetId == "master")
        rack = audioEngine != nullptr ? audioEngine->getMasterFxRackSnapshot() : nullptr;
    else if (parseTrackTarget(targetId, track))
    {
        const auto index = dataModel.getTrackIndex(track);
        rack = index >= 0 ? dataModel.getFxRackSnapshot(static_cast<size_t>(index)) : nullptr;
    }
    else
        rack = dataModel.getBusFxRackSnapshot({ static_cast<uint64_t>(targetId.getLargeIntValue()) });
    if (rack == nullptr) return options;
    for (size_t slot = 0; slot < rack->processors.size(); ++slot)
    {
        const auto& processor = rack->processors[slot];
        if (processor == nullptr) continue;
        options.push_back({ static_cast<int>(slot), identifierFor(targetId, static_cast<int>(slot), *processor),
                            processor->getName(), rack->bypass[slot] });
    }
    return options;
}

std::vector<PerformanceMacroService::ParameterOption> PerformanceMacroService::getParameterOptions(
    BusId bus, int pluginSlot, const juce::String& pluginIdentifier) const
{
    return getParameterOptions(juce::String(bus.value), pluginSlot, pluginIdentifier);
}

std::vector<PerformanceMacroService::ParameterOption> PerformanceMacroService::getParameterOptions(
    const juce::String& targetId, int pluginSlot, const juce::String& pluginIdentifier) const
{
    std::vector<ParameterOption> options;
    const auto candidate = preview(targetId, pluginSlot);
    if (! candidate.available || candidate.pluginIdentifier != pluginIdentifier) return options;
    const TrackDataModel::FxRackSnapshot* rack = nullptr;
    TrackId track;
    if (targetId == "master") rack = audioEngine != nullptr ? audioEngine->getMasterFxRackSnapshot() : nullptr;
    else if (parseTrackTarget(targetId, track))
    {
        const auto index = dataModel.getTrackIndex(track);
        rack = index >= 0 ? dataModel.getFxRackSnapshot(static_cast<size_t>(index)) : nullptr;
    }
    else rack = dataModel.getBusFxRackSnapshot({ static_cast<uint64_t>(targetId.getLargeIntValue()) });
    if (rack == nullptr || pluginSlot < 0 || pluginSlot >= static_cast<int>(rack->processors.size())) return options;
    const auto& processor = rack->processors[static_cast<size_t>(pluginSlot)];
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

PerformanceMacroService::Preview PerformanceMacroService::preview(BusId bus, int pluginSlot) const
{
    return preview(juce::String(bus.value), pluginSlot);
}

PerformanceMacroService::Preview PerformanceMacroService::preview(const juce::String& rawTargetId,
                                                                  int pluginSlot) const
{
    Preview result;
    const auto targetId = rawTargetId.trim();
    result.targetId = targetId;
    result.pluginSlot = pluginSlot;
    if (targetId.isEmpty())
    {
        result.error = "Choose a DAW target before choosing a plug-in";
        return result;
    }
    if (pluginSlot < 0 || pluginSlot >= static_cast<int>(TrackDataModel::maxFxSlots))
    {
        result.error = "The selected plug-in slot is outside this rack";
        return result;
    }

    const TrackDataModel::FxRackSnapshot* rack = nullptr;
    if (targetId == "master")
    {
        result.targetScope = TargetScope::master;
        result.targetName = "Master";
        result.busName = result.targetName;
        rack = audioEngine != nullptr ? audioEngine->getMasterFxRackSnapshot() : nullptr;
    }
    else if (parseTrackTarget(targetId, result.track))
    {
        result.targetScope = TargetScope::track;
        const auto index = dataModel.getTrackIndex(result.track);
        if (index >= 0)
        {
            result.targetName = dataModel.getTrack(static_cast<size_t>(index)).name;
            result.busName = result.targetName;
            rack = dataModel.getFxRackSnapshot(static_cast<size_t>(index));
        }
    }
    else
    {
        result.targetScope = TargetScope::bus;
        result.bus = { static_cast<uint64_t>(targetId.getLargeIntValue()) };
        const auto& buses = dataModel.getBuses();
        const auto found = std::find_if(buses.begin(), buses.end(), [&result] (const auto& state)
        {
            return state.id == result.bus;
        });
        if (found != buses.end())
        {
            result.targetName = found->name;
            result.busName = result.targetName;
            rack = dataModel.getBusFxRackSnapshot(result.bus);
        }
    }
    if (rack == nullptr)
    {
        result.error = "The selected DAW target no longer exists";
        return result;
    }
    if (rack == nullptr || rack->processors[static_cast<size_t>(pluginSlot)] == nullptr)
    {
        result.error = "The selected target slot is empty";
        return result;
    }

    const auto& processor = *rack->processors[static_cast<size_t>(pluginSlot)];
    result.available = true;
    result.bypassed = rack->bypass[static_cast<size_t>(pluginSlot)];
    result.pluginIdentifier = identifierFor(targetId, pluginSlot, processor);
    result.pluginName = processor.getName();
    result.proposal = PluginSemanticMapper::propose(result.pluginName, processor.getParameterDescriptors());
    return result;
}

PerformanceMacroService::Result PerformanceMacroService::apply(size_t macroIndex, BusId bus, int pluginSlot,
                                                                 bool confirmNeedsReview)
{
    return apply(macroIndex, juce::String(bus.value), pluginSlot, confirmNeedsReview);
}

PerformanceMacroService::Result PerformanceMacroService::apply(size_t macroIndex,
                                                                 const juce::String& targetId,
                                                                 int pluginSlot,
                                                                 bool confirmNeedsReview)
{
    Result result;
    if (! isValidMacroIndex(macroIndex))
    {
        result.error = "Unknown performance macro";
        return result;
    }

    const auto candidate = preview(targetId, pluginSlot);
    if (! candidate.available)
    {
        result.error = candidate.error;
        return result;
    }
    if (candidate.proposal.targets.empty())
    {
        result.error = "This plug-in has no safe smart mapping";
        return result;
    }
    if (candidate.proposal.needsReview && ! confirmNeedsReview)
    {
        result.error = "Smart mapping needs explicit confirmation";
        return result;
    }

    auto& macro = macros[macroIndex];
    macro.bus = candidate.bus;
    macro.track = candidate.track;
    macro.targetScope = candidate.targetScope;
    macro.targetId = candidate.targetId;
    macro.pluginSlot = candidate.pluginSlot;
    macro.busName = candidate.busName;
    macro.pluginIdentifier = candidate.pluginIdentifier;
    macro.pluginName = candidate.pluginName;
    macro.displayName = candidate.proposal.displayName;
    macro.mapping = candidate.proposal;
    macro.targets.clear();
    // A low-confidence proposal remains preview-only until the caller passes
    // confirmNeedsReview above. Once explicitly approved it is an active
    // mapping, not a perpetually unsafe one that can still receive values.
    macro.state = candidate.bypassed ? State::bypassed : State::active;
    refreshSnapshot(macro);
    result.succeeded = true;
    result.snapshot = macro;
    notifyChanged();
    return result;
}

PerformanceMacroService::Result PerformanceMacroService::applyParameter(
    size_t macroIndex, BusId bus, int pluginSlot, const juce::String& pluginIdentifier,
    const juce::String& parameterIdentifier, float minimum, float maximum, MacroCurve curve,
    bool invert, float smoothingMs)
{
    return applyParameter(macroIndex, juce::String(bus.value), pluginSlot, pluginIdentifier,
                          parameterIdentifier, minimum, maximum, curve, invert, smoothingMs);
}

PerformanceMacroService::Result PerformanceMacroService::applyParameter(
    size_t macroIndex, const juce::String& targetId, int pluginSlot, const juce::String& pluginIdentifier,
    const juce::String& parameterIdentifier, float minimum, float maximum, MacroCurve curve,
    bool invert, float smoothingMs)
{
    Result result;
    if (! isValidMacroIndex(macroIndex) || parameterIdentifier.isEmpty()
        || ! std::isfinite(minimum) || ! std::isfinite(maximum) || minimum > maximum)
    {
        result.error = "Macro target is invalid";
        return result;
    }
    const auto candidate = preview(targetId, pluginSlot);
    if (! candidate.available || candidate.pluginIdentifier != pluginIdentifier)
    {
        result.error = candidate.available ? "The selected plug-in instance changed" : candidate.error;
        return result;
    }
    const auto options = getParameterOptions(targetId, pluginSlot, pluginIdentifier);
    const auto found = std::find_if(options.begin(), options.end(), [&parameterIdentifier] (const auto& option)
    {
        return option.identifier == parameterIdentifier;
    });
    if (found == options.end() || ! found->stableIdentifier || ! found->automatable || found->readOnly)
    {
        result.error = "This plug-in parameter is not safely automatable";
        return result;
    }

    auto& macro = macros[macroIndex];
    macro.bus = candidate.bus;
    macro.track = candidate.track;
    macro.targetScope = candidate.targetScope;
    macro.targetId = candidate.targetId;
    macro.pluginSlot = candidate.pluginSlot;
    macro.busName = candidate.busName;
    macro.pluginIdentifier = candidate.pluginIdentifier;
    macro.pluginName = candidate.pluginName;
    macro.displayName = found->name;
    macro.mapping = {};
    macro.mapping.displayName = found->name;
    macro.mapping.confidence = 1.0f;
    macro.mapping.needsReview = false;
    // The existing realtime engine is normalized. Persist range/curve/invert
    // even when their first UI defaults are linear and non-inverted.
    macro.mapping.targets.push_back({ parameterIdentifier, found->name,
                                      PluginSemanticMapper::classify({ parameterIdentifier, found->name }),
                                      minimum, maximum, curve, invert,
                                      juce::jlimit(0.0f, 250.0f, smoothingMs) });
    macro.targets.clear();
    macro.state = candidate.bypassed ? State::bypassed : State::active;
    refreshSnapshot(macro);
    result.succeeded = true;
    result.snapshot = macro;
    notifyChanged();
    return result;
}

PerformanceMacroService::ParameterWriteResult PerformanceMacroService::setParameterValue(
    BusId bus, int pluginSlot, const juce::String& pluginIdentifier,
    const juce::String& parameterIdentifier, float normalisedValue)
{
    ParameterWriteResult result;
    if (! std::isfinite(normalisedValue) || parameterIdentifier.isEmpty())
    {
        result.error = "EQ parameter value is invalid";
        return result;
    }

    const auto candidate = preview(bus, pluginSlot);
    if (! candidate.available || candidate.pluginIdentifier != pluginIdentifier)
    {
        result.error = candidate.available ? "The selected plug-in instance changed" : candidate.error;
        return result;
    }

    const auto options = getParameterOptions(bus, pluginSlot, pluginIdentifier);
    const auto option = std::find_if(options.begin(), options.end(), [&parameterIdentifier] (const auto& item)
    {
        return item.identifier == parameterIdentifier;
    });
    if (option == options.end() || ! option->stableIdentifier || ! option->automatable || option->readOnly)
    {
        result.error = "This EQ parameter is not safely automatable";
        return result;
    }

    const auto* rack = dataModel.getBusFxRackSnapshot(bus);
    if (rack == nullptr || pluginSlot < 0 || pluginSlot >= static_cast<int>(rack->processors.size())
        || rack->processors[static_cast<size_t>(pluginSlot)] == nullptr)
    {
        result.error = "The selected EQ plug-in is no longer available";
        return result;
    }
    if (! rack->processors[static_cast<size_t>(pluginSlot)]->setParameterValue(
            parameterIdentifier, juce::jlimit(0.0f, 1.0f, normalisedValue)))
    {
        result.error = "The EQ plug-in rejected the parameter update";
        return result;
    }

    const auto refreshed = getParameterOptions(bus, pluginSlot, pluginIdentifier);
    const auto updated = std::find_if(refreshed.begin(), refreshed.end(), [&parameterIdentifier] (const auto& item)
    {
        return item.identifier == parameterIdentifier;
    });
    if (updated == refreshed.end())
    {
        result.error = "The EQ parameter disappeared after update";
        return result;
    }
    result.succeeded = true;
    result.parameter = *updated;
    notifyChanged();
    return result;
}

PerformanceMacroService::Result PerformanceMacroService::clear(size_t macroIndex)
{
    Result result;
    if (! isValidMacroIndex(macroIndex))
    {
        result.error = "Unknown performance macro";
        return result;
    }
    macros[macroIndex] = {};
    macros[macroIndex].macroIndex = macroIndex;
    result.succeeded = true;
    result.snapshot = macros[macroIndex];
    notifyChanged();
    return result;
}

PerformanceMacroService::Result PerformanceMacroService::setValue(size_t macroIndex, float normalisedValue)
{
    Result result;
    if (! isValidMacroIndex(macroIndex))
    {
        result.error = "Unknown performance macro";
        return result;
    }

    auto& macro = macros[macroIndex];
    refreshSnapshot(macro);
    if (macro.state != State::active)
    {
        result.error = "This macro has no active plug-in target";
        result.snapshot = macro;
        return result;
    }

    const TrackDataModel::FxRackSnapshot* rack = nullptr;
    TrackId track;
    if (macro.targetId == "master") rack = audioEngine != nullptr ? audioEngine->getMasterFxRackSnapshot() : nullptr;
    else if (parseTrackTarget(macro.targetId, track))
    {
        const auto index = dataModel.getTrackIndex(track);
        rack = index >= 0 ? dataModel.getFxRackSnapshot(static_cast<size_t>(index)) : nullptr;
    }
    else rack = dataModel.getBusFxRackSnapshot(macro.bus);
    if (rack == nullptr || macro.pluginSlot < 0 || macro.pluginSlot >= static_cast<int>(TrackDataModel::maxFxSlots))
    {
        result.error = "The mapped bus is no longer available";
        result.snapshot = macro;
        return result;
    }
    const auto& processor = rack->processors[static_cast<size_t>(macro.pluginSlot)];
    if (processor == nullptr || identifierFor(macro.targetId, macro.pluginSlot, *processor) != macro.pluginIdentifier)
    {
        result.error = "The mapped plug-in was replaced";
        macro.state = State::unassigned;
        result.snapshot = macro;
        notifyChanged();
        return result;
    }

    const auto value = juce::jlimit(0.0f, 1.0f, normalisedValue);
    for (const auto& target : macro.mapping.targets)
    {
        auto transformed = applyCurve(value, target.curve);
        if (target.invert) transformed = 1.0f - transformed;
        const auto mapped = target.minimum + (target.maximum - target.minimum) * transformed;
        if (! processor->setParameterValue(target.parameterIdentifier, mapped))
        {
            result.error = "A mapped plug-in parameter is no longer available";
            macro.state = State::unassigned;
            result.snapshot = macro;
            notifyChanged();
            return result;
        }
    }
    macro.value = value;
    refreshSnapshot(macro);
    result.succeeded = true;
    result.snapshot = macro;
    notifyChanged();
    return result;
}

PerformanceMacroService::Snapshot PerformanceMacroService::getSnapshot(size_t macroIndex) const
{
    if (! isValidMacroIndex(macroIndex)) return {};
    auto snapshot = macros[macroIndex];
    refreshSnapshot(snapshot);
    return snapshot;
}

void PerformanceMacroService::refresh()
{
    auto changed = false;
    for (auto& macro : macros)
    {
        const auto previous = macro;
        refreshSnapshot(macro);
        changed = changed || hasChanged(previous, macro);
    }
    if (changed) notifyChanged();
}

std::vector<PersistedPerformanceMacroState> PerformanceMacroService::createPersistedState() const
{
    std::vector<PersistedPerformanceMacroState> result;
    result.reserve(macros.size());
    for (const auto& source : macros)
    {
        if (source.state == State::unassigned || source.targetId.isEmpty())
            continue;

        PersistedPerformanceMacroState saved;
        saved.macroIndex = static_cast<int>(source.macroIndex);
        saved.state = static_cast<int>(source.state);
        saved.value = source.value;
        saved.bus = source.bus;
        saved.targetScope = source.targetScope == TargetScope::master ? "master"
                          : (source.targetScope == TargetScope::track ? "track" : "bus");
        saved.targetId = source.targetId;
        saved.pluginSlot = source.pluginSlot;
        saved.displayName = source.displayName;
        saved.pluginIdentifier = source.pluginIdentifier;
        for (const auto& target : source.mapping.targets)
            saved.targets.push_back({ target.parameterIdentifier, target.displayName,
                                      static_cast<int>(target.semantic), target.minimum, target.maximum,
                                      static_cast<int>(target.curve), target.invert, target.smoothingMs });
        result.push_back(std::move(saved));
    }
    return result;
}

void PerformanceMacroService::restorePersistedState(const std::vector<PersistedPerformanceMacroState>& state)
{
    for (size_t index = 0; index < macros.size(); ++index)
    {
        macros[index] = {};
        macros[index].macroIndex = index;
    }

    for (const auto& saved : state)
    {
        const auto targetId = saved.targetId.isNotEmpty() ? saved.targetId
                                                          : juce::String(saved.bus.value);
        if (saved.macroIndex < 0 || ! isValidMacroIndex(static_cast<size_t>(saved.macroIndex))
            || targetId.isEmpty() || saved.pluginSlot < 0
            || saved.pluginSlot >= static_cast<int>(TrackDataModel::maxFxSlots)
            || saved.pluginIdentifier.isEmpty())
            continue;

        auto& restored = macros[static_cast<size_t>(saved.macroIndex)];
        restored.bus = saved.bus;
        restored.targetId = targetId;
        restored.targetScope = saved.targetScope == "master" ? TargetScope::master
                             : (saved.targetScope == "track" ? TargetScope::track : TargetScope::bus);
        parseTrackTarget(targetId, restored.track);
        restored.pluginSlot = saved.pluginSlot;
        restored.pluginIdentifier = saved.pluginIdentifier;
        restored.displayName = saved.displayName.isNotEmpty() ? saved.displayName : "Needs Review";
        restored.value = juce::jlimit(0.0f, 1.0f, saved.value);
        restored.state = State::needsReview;
        for (const auto& target : saved.targets)
        {
            if (target.parameterIdentifier.isEmpty() || ! std::isfinite(target.minimum)
                || ! std::isfinite(target.maximum) || target.minimum > target.maximum)
                continue;
            restored.mapping.targets.push_back({ target.parameterIdentifier, target.displayName,
                                                  static_cast<PluginParameterSemantic>(target.semantic),
                                                  target.minimum, target.maximum,
                                                  static_cast<MacroCurve>(target.curve), target.invert,
                                                  target.smoothingMs });
        }

        const auto candidate = preview(targetId, saved.pluginSlot);
        if (! candidate.available || candidate.pluginIdentifier != saved.pluginIdentifier)
            continue;

        restored.bus = candidate.bus;
        restored.track = candidate.track;
        restored.targetScope = candidate.targetScope;
        restored.targetId = candidate.targetId;
        restored.busName = candidate.busName;
        restored.pluginName = candidate.pluginName;
        const auto descriptors = getParameterOptions(targetId, saved.pluginSlot, saved.pluginIdentifier);
        const auto parameterExists = [&descriptors] (const SmartMacroTarget& target)
        {
            return std::any_of(descriptors.begin(), descriptors.end(), [&target] (const auto& descriptor)
            {
                // Vendor IDs resolve directly. A generated host-index must
                // retain its expected display name too, preventing a silent
                // remap if a plug-in update reorders its parameter list.
                return descriptor.identifier == target.parameterIdentifier
                    && (! target.parameterIdentifier.startsWith("studioforge-index:")
                        || descriptor.name == target.displayName);
            });
        };
        const auto allTargetsResolve = ! restored.mapping.targets.empty()
            && std::all_of(restored.mapping.targets.begin(), restored.mapping.targets.end(),
                           [&parameterExists] (const auto& target) { return parameterExists(target); });
        if (allTargetsResolve)
        {
            restored.mapping.confidence = candidate.proposal.confidence;
            restored.mapping.needsReview = static_cast<State>(saved.state) == State::needsReview;
            restored.state = candidate.bypassed ? State::bypassed
                                                : (restored.mapping.needsReview ? State::needsReview : State::active);
        }
        refreshSnapshot(restored);
    }
    notifyChanged();
}

void PerformanceMacroService::refreshSnapshot(Snapshot& snapshot) const
{
    if (snapshot.targetId.isEmpty() || snapshot.pluginSlot < 0) return;
    const auto candidate = preview(snapshot.targetId, snapshot.pluginSlot);
    if (! candidate.available || candidate.pluginIdentifier != snapshot.pluginIdentifier)
    {
        snapshot.state = State::unassigned;
        snapshot.displayName = "Unassigned";
        snapshot.targets.clear();
        return;
    }

    // A persisted, unresolved mapping carries needsReview. An approved
    // low-confidence mapping remains active; confidence is still exposed to
    // the UI so it can show provenance without blocking the performer.
    snapshot.state = candidate.bypassed ? State::bypassed
                                         : (snapshot.state == State::needsReview ? State::needsReview : State::active);
    snapshot.busName = candidate.busName;
    snapshot.bus = candidate.bus;
    snapshot.track = candidate.track;
    snapshot.targetScope = candidate.targetScope;
    snapshot.pluginName = candidate.pluginName;
    snapshot.targets.clear();

    const TrackDataModel::FxRackSnapshot* rack = nullptr;
    TrackId track;
    if (snapshot.targetId == "master") rack = audioEngine != nullptr ? audioEngine->getMasterFxRackSnapshot() : nullptr;
    else if (parseTrackTarget(snapshot.targetId, track))
    {
        const auto index = dataModel.getTrackIndex(track);
        rack = index >= 0 ? dataModel.getFxRackSnapshot(static_cast<size_t>(index)) : nullptr;
    }
    else rack = dataModel.getBusFxRackSnapshot(snapshot.bus);
    if (rack == nullptr) return;
    const auto& processor = rack->processors[static_cast<size_t>(snapshot.pluginSlot)];
    const auto descriptors = processor->getParameterDescriptors();
    for (const auto& target : snapshot.mapping.targets)
    {
        Snapshot::TargetState state;
        state.parameterIdentifier = target.parameterIdentifier;
        state.displayName = target.displayName;
        state.semantic = target.semantic;
        state.valueText = processor->getParameterText(target.parameterIdentifier);
        snapshot.targets.push_back(std::move(state));
    }

    // A macro with one target behaves like a hardware MIDI controller: when
    // the performer turns the plug-in GUI, the THM faceplate follows.  Multi
    // target smart mappings intentionally retain their last macro position,
    // because a single inverse cannot represent several independent values.
    if (snapshot.mapping.targets.size() == 1)
    {
        const auto& target = snapshot.mapping.targets.front();
        const auto descriptor = std::find_if(descriptors.begin(), descriptors.end(), [&target] (const auto& item)
        {
            return item.identifier == target.parameterIdentifier && item.stableIdentifier;
        });
        const auto range = target.maximum - target.minimum;
        if (descriptor != descriptors.end() && range > 0.000001f)
        {
            auto shaped = (descriptor->currentNormalised - target.minimum) / range;
            if (target.invert) shaped = 1.0f - shaped;
            snapshot.value = invertCurve(shaped, target.curve);
        }
    }
}

bool PerformanceMacroService::hasChanged(const Snapshot& before, const Snapshot& after)
{
    if (before.state != after.state || before.displayName != after.displayName || before.value != after.value
        || before.targetId != after.targetId || before.targetScope != after.targetScope
        || before.busName != after.busName || before.pluginName != after.pluginName
        || before.targets.size() != after.targets.size())
        return true;

    for (size_t index = 0; index < before.targets.size(); ++index)
    {
        const auto& lhs = before.targets[index];
        const auto& rhs = after.targets[index];
        if (lhs.parameterIdentifier != rhs.parameterIdentifier || lhs.displayName != rhs.displayName
            || lhs.semantic != rhs.semantic || lhs.valueText != rhs.valueText)
            return true;
    }
    return false;
}

void PerformanceMacroService::changeListenerCallback(juce::ChangeBroadcaster*)
{
    refresh();
}

void PerformanceMacroService::notifyChanged()
{
    ++revision;
    sendChangeMessage();
}
