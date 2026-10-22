#pragma once
#include "core/RoutingCore.h"
#include <CoreAudio/CoreAudio.h>
#include <atomic>
#include <memory>
#include <string>
#include <vector>

namespace studioforge::link {
struct NativeDevice { AudioDeviceID id {}; std::string name, uid; unsigned inputs {}, outputs {}; bool alive {}; };
std::vector<NativeDevice> enumerateDevices(std::string& error);
// One full-duplex device and one clock only. Control methods use one thread.
class NativeAudio final {
public:
    ~NativeAudio();
    bool start(AudioDeviceID device, float gain, std::string& error);
    void stop() noexcept;
    bool setGain(float gain, std::string& error);
    std::string status() const;
private:
    static OSStatus callback(AudioObjectID, const AudioTimeStamp*, const AudioBufferList*,
                             const AudioTimeStamp*, AudioBufferList*, const AudioTimeStamp*, void*) noexcept;
    static OSStatus devicePropertyChanged(AudioObjectID, UInt32, const AudioObjectPropertyAddress*, void*) noexcept;
    AudioDeviceID deviceId = kAudioObjectUnknown;
    AudioDeviceIOProcID callbackId = nullptr;
    std::unique_ptr<RoutingCore> core;
    RoutingConfig config;
    std::size_t frameCapacity = 0;
    std::atomic<bool> started { false }, callbackSeen { false }, unsupportedBuffer { false }, deviceLost { false };
    std::atomic<std::uint64_t> callbacks { 0 };
};
}
