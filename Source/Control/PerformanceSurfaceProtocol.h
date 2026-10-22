#pragma once

#include "PerformanceMacroService.h"

class AudioEngine;
class PitchCorrectionIntegrationService;

// Transport-neutral boundary for the local Tune-AI control surface.  The
// socket/pipe implementation only forwards UTF-8 JSON to this class; all
// authentication, revision and plug-in identity checks remain here where they
// can be tested without opening a network endpoint.
class PerformanceSurfaceProtocol final
{
public:
    PerformanceSurfaceProtocol(TrackDataModel& model, PerformanceMacroService& macros,
                               juce::String sessionToken, AudioEngine* engine = nullptr,
                               PitchCorrectionIntegrationService* pitchCorrection = nullptr);

    juce::String makeStatePayload() const;
    juce::String handleCommand(const juce::String& requestJson);

private:
    juce::String makeError(const juce::String& message) const;
    juce::var makeAudioAnalysisValue() const;
    juce::String makeAudioAnalysisPayload() const;
    juce::String makeSnapshotPayload(const PerformanceMacroService::Snapshot& snapshot) const;
    bool validateEnvelope(const juce::DynamicObject& request, juce::String& error) const;
    static juce::var snapshotToVar(const PerformanceMacroService::Snapshot& snapshot);

    TrackDataModel& dataModel;
    PerformanceMacroService& macroService;
    juce::String token;
    AudioEngine* audioEngine = nullptr;
    PitchCorrectionIntegrationService* pitchCorrection = nullptr;
};
