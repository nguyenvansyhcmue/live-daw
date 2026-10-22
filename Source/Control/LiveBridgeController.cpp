#include "LiveBridgeController.h"
#include "AudioEngine/AudioEngine.h"

#include <algorithm>
#include <cmath>

#if JUCE_MAC
 #include <CoreAudio/CoreAudio.h>
 #include <CoreFoundation/CoreFoundation.h>
#endif

namespace {
bool nearlyEqual(double lhs, double rhs) noexcept
{
    return std::abs(lhs - rhs) < 0.01;
}
}

bool liveBridgeEndpointSupportsRate(const LiveBridgeEndpoint& endpoint, double rate) noexcept
{
    if (rate <= 0.0) return false;
    if (std::any_of(endpoint.sampleRates.begin(), endpoint.sampleRates.end(),
                    [rate] (double candidate) { return nearlyEqual(candidate, rate); }))
        return true;
    return std::any_of(endpoint.sampleRateRanges.begin(), endpoint.sampleRateRanges.end(),
                       [rate] (const auto& range) { return rate >= range.minimum - 0.01 && rate <= range.maximum + 0.01; });
}

bool isLiveBridgeEndpointCompatible(const LiveBridgeEndpoint& endpoint, double rate) noexcept
{
    return endpoint.alive && endpoint.isVirtualDevice && endpoint.outputChannels >= 2
        && liveBridgeEndpointSupportsRate(endpoint, rate);
}

std::string normaliseLiveBridgeEndpointUid(std::string uid)
{
    const auto first = uid.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return {};
    const auto last = uid.find_last_not_of(" \t\r\n");
    uid = uid.substr(first, last - first + 1);
    if (uid.size() > 1024
        || std::any_of(uid.begin(), uid.end(), [] (unsigned char character) { return character < 0x20 || character == 0x7f; }))
        return {};
    return uid;
}

LiveBridgeController::LiveBridgeController(LiveBridgeEndpointProvider& source, LiveBridgeOutputPort& port)
    : endpoints(source), output(port) {}

void LiveBridgeController::setPreferredEndpointUid(std::string uid) { preferredUid = normaliseLiveBridgeEndpointUid(std::move(uid)); }
void LiveBridgeController::setFallbackEndpointUid(std::string uid) { fallbackUid = normaliseLiveBridgeEndpointUid(std::move(uid)); }

const LiveBridgeEndpoint* LiveBridgeController::selectCompatible(const std::vector<LiveBridgeEndpoint>& all, double rate) const
{
    const auto findUid = [&] (const std::string& uid) -> const LiveBridgeEndpoint*
    {
        if (uid.empty()) return nullptr;
        const auto found = std::find_if(all.begin(), all.end(), [&] (const auto& endpoint) { return endpoint.uid == uid; });
        return found != all.end() && isLiveBridgeEndpointCompatible(*found, rate) ? &*found : nullptr;
    };
    return findUid(preferredUid) != nullptr ? findUid(preferredUid) : findUid(fallbackUid);
}

void LiveBridgeController::fail(std::string message)
{
    output.disconnect(); connectedUid.clear(); lastError = std::move(message); currentState = LiveBridgeState::error;
}

bool LiveBridgeController::connect(std::uint64_t nowMs)
{
    // A second control-thread request while a route is healthy is harmless
    // and must not open a second secondary device session.
    if ((currentState == LiveBridgeState::ready || currentState == LiveBridgeState::active) && output.configured())
        return true;
    if (currentState == LiveBridgeState::preparing)
        return false;
    disconnect(); currentState = LiveBridgeState::preparing;
    std::string discoveryError;
    const auto all = endpoints.discover(discoveryError);
    if (!discoveryError.empty()) { fail(discoveryError); return false; }
    const auto rate = output.primarySampleRate();
    if (rate <= 0.0) { fail("Primary audio device has no valid sample rate"); return false; }
    const auto* endpoint = selectCompatible(all, rate);
    if (!endpoint) { fail("No configured compatible live output endpoint at " + std::to_string(rate) + " Hz"); return false; }
    std::string connectError;
    if (!output.connectUid(endpoint->uid, connectError) || !output.configured())
    {
        fail(connectError.empty() ? "Stream output endpoint did not start" : connectError); return false;
    }
    connectedUid = endpoint->uid; lastError.clear(); callbacksAtReady = lastCallbackCount = output.callbackCount();
    lastProgressMs = nowMs; currentState = LiveBridgeState::ready; return true;
}

void LiveBridgeController::poll(std::uint64_t nowMs)
{
    if (currentState != LiveBridgeState::ready && currentState != LiveBridgeState::active) return;
    if (!output.configured()) { fail("Live output endpoint disconnected"); return; }
    const auto callbacks = output.callbackCount();
    if (callbacks > lastCallbackCount) { lastCallbackCount = callbacks; lastProgressMs = nowMs; currentState = LiveBridgeState::active; return; }
    // READY may legitimately wait for the device's first callback; ACTIVE may
    // not remain stale indefinitely. This timer is control-thread only.
    if (currentState == LiveBridgeState::active && nowMs - lastProgressMs > 2000)
        fail("Live output callback stalled");
}

void LiveBridgeController::disconnect()
{
    output.disconnect(); connectedUid.clear(); lastError.clear(); callbacksAtReady = lastCallbackCount = lastProgressMs = 0;
    currentState = LiveBridgeState::off;
}

AudioEngineLiveBridgeOutputPort::AudioEngineLiveBridgeOutputPort(AudioEngine& value) : engine(value) {}
double AudioEngineLiveBridgeOutputPort::primarySampleRate() const { return engine.getPrimaryAudioSampleRate(); }
bool AudioEngineLiveBridgeOutputPort::connectUid(const std::string& uid, std::string& error)
{
    const auto result = engine.selectStreamOutputDeviceByUid(juce::String::fromUTF8(uid.c_str()));
    error = result.getErrorMessage().toStdString(); return result.wasOk();
}
void AudioEngineLiveBridgeOutputPort::disconnect() { static_cast<void>(engine.selectStreamOutputDevice({})); }
bool AudioEngineLiveBridgeOutputPort::configured() const { return engine.isStreamOutputConfigured(); }
std::uint64_t AudioEngineLiveBridgeOutputPort::callbackCount() const { return engine.getStreamOutputCallbackCount(); }

std::vector<LiveBridgeEndpoint> NativeLiveBridgeEndpointProvider::discover(std::string& error) const
{
#if JUCE_MAC
    AudioObjectPropertyAddress address { kAudioHardwarePropertyDevices, kAudioObjectPropertyScopeGlobal, kAudioObjectPropertyElementMain };
    UInt32 bytes = 0;
    if (const auto status = AudioObjectGetPropertyDataSize(kAudioObjectSystemObject, &address, 0, nullptr, &bytes); status != noErr)
    { error = "Core Audio device enumeration failed: " + std::to_string(status); return {}; }
    if (bytes == 0) { error = "Core Audio returned no audio devices"; return {}; }
    std::vector<AudioDeviceID> ids(bytes / sizeof(AudioDeviceID));
    if (const auto status = AudioObjectGetPropertyData(kAudioObjectSystemObject, &address, 0, nullptr, &bytes, ids.data()); status != noErr)
    { error = "Core Audio device enumeration failed: " + std::to_string(status); return {}; }
    std::vector<LiveBridgeEndpoint> result;
    for (auto id : ids)
    {
        auto cfString = [&] (AudioObjectPropertySelector selector) {
            AudioObjectPropertyAddress p { selector, kAudioObjectPropertyScopeGlobal, kAudioObjectPropertyElementMain }; CFStringRef value = nullptr; UInt32 size = sizeof(value);
            if (AudioObjectGetPropertyData(id, &p, 0, nullptr, &size, &value) != noErr || value == nullptr) return std::string {};
            char text[1024] {}; const auto ok = CFStringGetCString(value, text, sizeof(text), kCFStringEncodingUTF8); CFRelease(value); return ok ? std::string(text) : std::string {};
        };
        AudioObjectPropertyAddress aliveP { kAudioDevicePropertyDeviceIsAlive, kAudioObjectPropertyScopeGlobal, kAudioObjectPropertyElementMain }; UInt32 alive = 0, aliveSize = sizeof(alive);
        AudioObjectPropertyAddress transportP { kAudioDevicePropertyTransportType, kAudioObjectPropertyScopeGlobal, kAudioObjectPropertyElementMain }; UInt32 transport = 0, transportSize = sizeof(transport);
        AudioObjectPropertyAddress currentRateP { kAudioDevicePropertyNominalSampleRate, kAudioObjectPropertyScopeGlobal, kAudioObjectPropertyElementMain }; Float64 currentRate = 0.0; UInt32 currentRateSize = sizeof(currentRate);
        AudioObjectPropertyAddress cfgP { kAudioDevicePropertyStreamConfiguration, kAudioObjectPropertyScopeOutput, kAudioObjectPropertyElementMain }; UInt32 cfgSize = 0;
        if (AudioObjectGetPropertyDataSize(id, &cfgP, 0, nullptr, &cfgSize) != noErr || cfgSize < sizeof(AudioBufferList)) continue;
        std::vector<std::uint64_t> storage((cfgSize + 7) / 8); auto* cfg = reinterpret_cast<AudioBufferList*>(storage.data());
        if (AudioObjectGetPropertyData(id, &cfgP, 0, nullptr, &cfgSize, cfg) != noErr) continue;
        unsigned channels = 0; for (UInt32 i = 0; i < cfg->mNumberBuffers; ++i) channels += cfg->mBuffers[i].mNumberChannels;
        AudioObjectGetPropertyData(id, &aliveP, 0, nullptr, &aliveSize, &alive);
        AudioObjectGetPropertyData(id, &transportP, 0, nullptr, &transportSize, &transport);
        AudioObjectGetPropertyData(id, &currentRateP, 0, nullptr, &currentRateSize, &currentRate);
        AudioObjectPropertyAddress ratesP { kAudioDevicePropertyAvailableNominalSampleRates, kAudioObjectPropertyScopeGlobal, kAudioObjectPropertyElementMain }; UInt32 ratesSize = 0;
        std::vector<double> rates;
        std::vector<LiveBridgeSampleRateRange> rateRanges;
        if (AudioObjectGetPropertyDataSize(id, &ratesP, 0, nullptr, &ratesSize) == noErr && ratesSize >= sizeof(AudioValueRange)) {
            std::vector<AudioValueRange> ranges(ratesSize / sizeof(AudioValueRange));
            if (AudioObjectGetPropertyData(id, &ratesP, 0, nullptr, &ratesSize, ranges.data()) == noErr)
                for (const auto& range : ranges)
                {
                    rateRanges.push_back({ range.mMinimum, range.mMaximum });
                    if (nearlyEqual(range.mMinimum, range.mMaximum)) rates.push_back(range.mMinimum);
                }
        }
        const auto uid = cfString(kAudioDevicePropertyDeviceUID);
        if (uid.empty()) continue;
        const auto virtualDevice = transport == kAudioDeviceTransportTypeVirtual;
        const auto label = virtualDevice ? std::string("Virtual") : std::string("Non-virtual");
        result.push_back({ uid, cfString(kAudioObjectPropertyName), channels, alive != 0,
                           std::move(rates), virtualDevice, transport, label, currentRate, std::move(rateRanges) });
    }
    error.clear(); return result;
#else
    error = "Native live endpoint discovery is not implemented on this platform"; return {};
#endif
}
