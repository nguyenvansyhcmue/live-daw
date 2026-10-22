#pragma once

#include "PerformanceSurfaceProtocol.h"

// A local-only transport for the external Tune-AI performance surface. On
// macOS/Linux it prefers a Unix-domain socket and also publishes a short-lived
// loopback fallback for packaged app environments that deny Unix sockets. It
// never carries audio; every request still requires the random session token.
class PerformanceSurfaceBridge final : private juce::Thread
{
public:
    PerformanceSurfaceBridge(TrackDataModel& model, PerformanceMacroService& macros,
                             AudioEngine* engine = nullptr,
                             PitchCorrectionIntegrationService* pitchCorrection = nullptr);
    ~PerformanceSurfaceBridge() override;

    juce::Result start();
    void stop();
    juce::File getConfigurationFile() const;

private:
    void run() override;
    juce::String dispatchOnMessageThread(const juce::String& request);
    juce::Result writeConfiguration() const;

    TrackDataModel& dataModel;
    PerformanceMacroService& macros;
    AudioEngine* audioEngine = nullptr;
    PitchCorrectionIntegrationService* pitchCorrection = nullptr;
    juce::String sessionToken;
    juce::String socketPath;
    int listeningSocket = -1;
    int loopbackListeningSocket = -1;
    int loopbackPort = 0;
    std::atomic<bool> accepting { false };
};
