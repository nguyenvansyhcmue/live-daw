#pragma once

#include "PluginSemanticMapper.h"
#include "../Models/TrackDataModel.h"
#include "../Project/ProjectState.h"

#include <array>

class AudioEngine;

class PerformanceMacroService final : public juce::ChangeBroadcaster,
                                      private juce::ChangeListener
{
public:
    static constexpr size_t macroCount = 6;

    enum class State : uint8_t { unassigned, needsReview, active, bypassed };
    enum class TargetScope : uint8_t { bus, track, master };

    struct BusOption
    {
        BusId id;
        juce::String name;
    };

    struct PluginOption
    {
        int slot = -1;
        juce::String identifier;
        juce::String name;
        bool bypassed = false;
    };

    struct ParameterOption
    {
        juce::String identifier;
        juce::String name;
        juce::String groupPath;
        juce::String unit;
        juce::String valueText;
        float value = 0.0f;
        float defaultValue = 0.0f;
        bool automatable = false;
        bool readOnly = false;
        bool stableIdentifier = false;
        juce::String category;
        juce::String role;
        float importance = 0.0f;
        bool recommended = false;
        bool safeForMacro = false;
        int dangerLevel = 0;
        juce::String recommendationReason;
    };

    struct Preview
    {
        bool available = false;
        bool bypassed = false;
        BusId bus;
        TrackId track;
        TargetScope targetScope = TargetScope::bus;
        juce::String targetId;
        juce::String targetName;
        int pluginSlot = -1;
        juce::String busName;
        juce::String pluginIdentifier;
        juce::String pluginName;
        SmartMacroProposal proposal;
        juce::String error;
    };

    struct Snapshot
    {
        struct TargetState
        {
            juce::String parameterIdentifier;
            juce::String displayName;
            PluginParameterSemantic semantic = PluginParameterSemantic::unknown;
            juce::String valueText;
        };

        size_t macroIndex = 0;
        State state = State::unassigned;
        float value = 0.0f;
        BusId bus;
        TrackId track;
        TargetScope targetScope = TargetScope::bus;
        juce::String targetId;
        int pluginSlot = -1;
        juce::String displayName = "Unassigned";
        juce::String busName;
        juce::String pluginIdentifier;
        juce::String pluginName;
        SmartMacroProposal mapping;
        // This is refreshed from the processor on the control/UI thread. It
        // lets a remote surface say exactly what a macro is changing rather
        // than inventing labels such as "short reverb" or "echo".
        std::vector<TargetState> targets;
    };

    struct Result
    {
        bool succeeded = false;
        Snapshot snapshot;
        juce::String error;
    };

    // Direct parameter writes are reserved for a verified EQ control surface.
    // Unlike a macro assignment, this is not persisted and must always carry
    // the current bus/slot/instance identity supplied by the caller.
    struct ParameterWriteResult
    {
        bool succeeded = false;
        ParameterOption parameter;
        juce::String error;
    };

    explicit PerformanceMacroService(TrackDataModel& model, AudioEngine* engine = nullptr);
    ~PerformanceMacroService() override;

    std::vector<BusOption> getBusOptions() const;
    std::vector<PluginOption> getPluginOptions(BusId bus) const;
    std::vector<PluginOption> getPluginOptions(const juce::String& targetId) const;
    std::vector<ParameterOption> getParameterOptions(BusId bus, int pluginSlot,
                                                      const juce::String& pluginIdentifier) const;
    std::vector<ParameterOption> getParameterOptions(const juce::String& targetId, int pluginSlot,
                                                      const juce::String& pluginIdentifier) const;
    Preview preview(BusId bus, int pluginSlot) const;
    Preview preview(const juce::String& targetId, int pluginSlot) const;
    Result apply(size_t macroIndex, BusId bus, int pluginSlot, bool confirmNeedsReview = false);
    Result apply(size_t macroIndex, const juce::String& targetId, int pluginSlot,
                 bool confirmNeedsReview = false);
    Result applyParameter(size_t macroIndex, BusId bus, int pluginSlot,
                          const juce::String& pluginIdentifier, const juce::String& parameterIdentifier,
                          float minimum, float maximum, MacroCurve curve, bool invert, float smoothingMs);
    Result applyParameter(size_t macroIndex, const juce::String& targetId, int pluginSlot,
                          const juce::String& pluginIdentifier, const juce::String& parameterIdentifier,
                          float minimum, float maximum, MacroCurve curve, bool invert, float smoothingMs);
    Result clear(size_t macroIndex);
    Result setValue(size_t macroIndex, float normalisedValue);
    ParameterWriteResult setParameterValue(BusId bus, int pluginSlot,
                                           const juce::String& pluginIdentifier,
                                           const juce::String& parameterIdentifier,
                                           float normalisedValue);
    Snapshot getSnapshot(size_t macroIndex) const;
    void refresh();
    std::vector<PersistedPerformanceMacroState> createPersistedState() const;
    // Restoring never retargets by name. A missing/replaced plug-in or
    // parameter becomes Needs Review and must be approved by the performer.
    void restorePersistedState(const std::vector<PersistedPerformanceMacroState>& state);

private:
    static bool isValidMacroIndex(size_t macroIndex) noexcept;
    static juce::String identifierFor(BusId bus, int pluginSlot, const AudioEffectProcessor& processor);
    static juce::String identifierFor(const juce::String& targetId, int pluginSlot,
                                      const AudioEffectProcessor& processor);
    static bool hasChanged(const Snapshot& before, const Snapshot& after);
    void changeListenerCallback(juce::ChangeBroadcaster*) override;
    void refreshSnapshot(Snapshot& snapshot) const;
    void notifyChanged();

    TrackDataModel& dataModel;
    AudioEngine* audioEngine = nullptr;
    std::array<Snapshot, macroCount> macros;
    uint64_t revision = 0;
};
