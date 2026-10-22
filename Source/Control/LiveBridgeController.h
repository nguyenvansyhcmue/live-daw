#pragma once

#include <cstdint>
#include <string>
#include <vector>

class AudioEngine;

enum class LiveBridgeState : std::uint8_t { off, preparing, ready, active, error };

struct LiveBridgeSampleRateRange final
{
    double minimum = 0.0;
    double maximum = 0.0;
};

struct LiveBridgeEndpoint final
{
    std::string uid;          // Persistent identity; never an AudioDeviceID.
    std::string displayName;  // Used only to open JUCE's named device.
    unsigned outputChannels = 0;
    bool alive = false;
    std::vector<double> sampleRates;
    // Populated from Core Audio transport metadata; this is deliberately not
    // inferred from a friendly device name.
    bool isVirtualDevice = false;
    std::uint32_t transportType = 0;
    std::string transportLabel;
    double currentSampleRate = 0.0;
    std::vector<LiveBridgeSampleRateRange> sampleRateRanges;
};

[[nodiscard]] bool liveBridgeEndpointSupportsRate(const LiveBridgeEndpoint&, double sampleRate) noexcept;
[[nodiscard]] bool isLiveBridgeEndpointCompatible(const LiveBridgeEndpoint&, double sampleRate) noexcept;
[[nodiscard]] std::string normaliseLiveBridgeEndpointUid(std::string uid);

class LiveBridgeEndpointProvider
{
public:
    virtual ~LiveBridgeEndpointProvider() = default;
    virtual std::vector<LiveBridgeEndpoint> discover(std::string& error) const = 0;
};

class LiveBridgeOutputPort
{
public:
    virtual ~LiveBridgeOutputPort() = default;
    virtual double primarySampleRate() const = 0;
    virtual bool connectUid(const std::string& uid, std::string& error) = 0;
    virtual void disconnect() = 0;
    virtual bool configured() const = 0;
    virtual std::uint64_t callbackCount() const = 0;
};

// Control-thread state machine. It owns no PCM and never changes the main
// monitor device; AudioEngine's existing StreamOutputBridge remains the only
// stream-audio path.
class LiveBridgeController final
{
public:
    LiveBridgeController(LiveBridgeEndpointProvider&, LiveBridgeOutputPort&);
    void setPreferredEndpointUid(std::string uid);
    void setFallbackEndpointUid(std::string uid);
    [[nodiscard]] const std::string& preferredEndpointUid() const noexcept { return preferredUid; }
    [[nodiscard]] const std::string& fallbackEndpointUid() const noexcept { return fallbackUid; }
    [[nodiscard]] LiveBridgeState state() const noexcept { return currentState; }
    [[nodiscard]] const std::string& error() const noexcept { return lastError; }
    [[nodiscard]] const std::string& activeEndpointUid() const noexcept { return connectedUid; }

    bool connect(std::uint64_t nowMs);
    void poll(std::uint64_t nowMs);
    void disconnect();

private:
    const LiveBridgeEndpoint* selectCompatible(const std::vector<LiveBridgeEndpoint>&, double sampleRate) const;
    void fail(std::string message);
    LiveBridgeEndpointProvider& endpoints;
    LiveBridgeOutputPort& output;
    std::string preferredUid, fallbackUid, connectedUid, lastError;
    LiveBridgeState currentState = LiveBridgeState::off;
    std::uint64_t callbacksAtReady = 0, lastCallbackCount = 0, lastProgressMs = 0;
};

// Production adapters. The provider uses Core Audio UID discovery on macOS;
// the port delegates connection and callback state to AudioEngine.
class NativeLiveBridgeEndpointProvider final : public LiveBridgeEndpointProvider
{
public:
    std::vector<LiveBridgeEndpoint> discover(std::string& error) const override;
};

class AudioEngineLiveBridgeOutputPort final : public LiveBridgeOutputPort
{
public:
    explicit AudioEngineLiveBridgeOutputPort(AudioEngine&);
    double primarySampleRate() const override;
    bool connectUid(const std::string&, std::string& error) override;
    void disconnect() override;
    bool configured() const override;
    std::uint64_t callbackCount() const override;
private:
    AudioEngine& engine;
};
