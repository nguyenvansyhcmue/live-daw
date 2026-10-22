#include "NativeAudio.h"
#include <CoreFoundation/CoreFoundation.h>
#include <algorithm>
#include <cmath>
#include <cstring>

namespace studioforge::link {
namespace {
AudioObjectPropertyAddress property(AudioObjectPropertySelector selector, AudioObjectPropertyScope scope = kAudioObjectPropertyScopeGlobal)
{ return { selector, scope, kAudioObjectPropertyElementMain }; }
std::string stringProperty(AudioObjectID id, AudioObjectPropertySelector selector)
{
    auto p = property(selector); CFStringRef value = nullptr; UInt32 size = sizeof(value);
    if (AudioObjectGetPropertyData(id, &p, 0, nullptr, &size, &value) != noErr || ! value) return {};
    auto length = CFStringGetMaximumSizeForEncoding(CFStringGetLength(value), kCFStringEncodingUTF8) + 1;
    std::vector<char> text(static_cast<std::size_t>(length));
    const bool ok = CFStringGetCString(value, text.data(), length, kCFStringEncodingUTF8);
    CFRelease(value); return ok ? std::string(text.data()) : std::string {};
}
unsigned channels(AudioDeviceID id, AudioObjectPropertyScope scope)
{
    auto p = property(kAudioDevicePropertyStreamConfiguration, scope); UInt32 size = 0;
    if (AudioObjectGetPropertyDataSize(id, &p, 0, nullptr, &size) != noErr || size < sizeof(AudioBufferList)) return 0;
    std::vector<std::uint64_t> memory((size + 7) / 8);
    auto* list = reinterpret_cast<AudioBufferList*>(memory.data());
    if (AudioObjectGetPropertyData(id, &p, 0, nullptr, &size, list) != noErr) return 0;
    unsigned count = 0; for (UInt32 i = 0; i < list->mNumberBuffers; ++i) count += list->mBuffers[i].mNumberChannels;
    return count;
}
bool alive(AudioDeviceID id)
{
    UInt32 state = 0, size = sizeof(state); auto p = property(kAudioDevicePropertyDeviceIsAlive);
    return AudioObjectGetPropertyData(id, &p, 0, nullptr, &size, &state) == noErr && state != 0;
}
bool formatSupported(AudioDeviceID id, AudioObjectPropertyScope scope, double& rate)
{
    AudioStreamBasicDescription format {}; UInt32 size = sizeof(format); auto p = property(kAudioDevicePropertyStreamFormat, scope);
    if (AudioObjectGetPropertyData(id, &p, 0, nullptr, &size, &format) != noErr) return false;
    rate = format.mSampleRate;
    return format.mFormatID == kAudioFormatLinearPCM && (format.mFormatFlags & kAudioFormatFlagIsFloat)
        && (format.mFormatFlags & kAudioFormatFlagIsNonInterleaved) && format.mBitsPerChannel == 32
        && format.mBytesPerFrame == sizeof(float) && rate > 0.0;
}
}
std::vector<NativeDevice> enumerateDevices(std::string& error)
{
    auto p = property(kAudioHardwarePropertyDevices); UInt32 size = 0;
    auto status = AudioObjectGetPropertyDataSize(kAudioObjectSystemObject, &p, 0, nullptr, &size);
    if (status != noErr) { error = "Core Audio enumeration failed: " + std::to_string(status); return {}; }
    std::vector<AudioDeviceID> ids(size / sizeof(AudioDeviceID));
    if (size && (status = AudioObjectGetPropertyData(kAudioObjectSystemObject, &p, 0, nullptr, &size, ids.data())) != noErr)
    { error = "Core Audio enumeration failed: " + std::to_string(status); return {}; }
    ids.resize(size / sizeof(AudioDeviceID)); std::vector<NativeDevice> result;
    for (auto id : ids) result.push_back({ id, stringProperty(id, kAudioObjectPropertyName), stringProperty(id, kAudioDevicePropertyDeviceUID),
                                            channels(id, kAudioDevicePropertyScopeInput), channels(id, kAudioDevicePropertyScopeOutput), alive(id) });
    error.clear(); return result;
}
NativeAudio::~NativeAudio() { stop(); }
bool NativeAudio::start(AudioDeviceID id, float gain, std::string& error)
{
    if (started.load()) { error = "Stop current stream first"; return false; }
    if (! std::isfinite(gain) || gain < 0 || gain > 1) { error = "Volume must be between 0 and 1"; return false; }
    if (! alive(id) || channels(id, kAudioDevicePropertyScopeInput) < 1 || channels(id, kAudioDevicePropertyScopeOutput) < 2)
    { error = "Device unavailable or not duplex (input and stereo output required)"; return false; }
    double inRate = 0, outRate = 0;
    if (! formatSupported(id, kAudioDevicePropertyScopeInput, inRate) || ! formatSupported(id, kAudioDevicePropertyScopeOutput, outRate) || inRate != outRate)
    { error = "Unsupported format: matching non-interleaved Float32 input and output required"; return false; }
    AudioValueRange range {}; UInt32 size = sizeof(range); auto p = property(kAudioDevicePropertyBufferFrameSizeRange);
    if (AudioObjectGetPropertyData(id, &p, 0, nullptr, &size, &range) != noErr || ! std::isfinite(range.mMaximum) || range.mMaximum < 1 || range.mMaximum > 32768)
    { error = "Cannot determine safe device buffer bound"; return false; }
    frameCapacity = static_cast<std::size_t>(std::ceil(range.mMaximum)); core = std::make_unique<RoutingCore>(2, 1, frameCapacity);
    config = {}; config.endpoints = { { 1, EndpointKind::source }, { 2, EndpointKind::destination } };
    config.routes = { { 1, 2, { 0, 1 }, gain, false } };
    if (! core->publish(config, error)) { core.reset(); return false; }
    callbackSeen.store(false); unsupportedBuffer.store(false); callbacks.store(0); deviceId = id;
    deviceLost.store(false, std::memory_order_release);
    auto aliveProperty = property(kAudioDevicePropertyDeviceIsAlive);
    auto status = AudioObjectAddPropertyListener(deviceId, &aliveProperty, devicePropertyChanged, this);
    if (status != noErr)
    {
        error = "Cannot monitor Core Audio device state (" + std::to_string(status) + ")";
        deviceId = kAudioObjectUnknown; core.reset(); return false;
    }
    status = AudioDeviceCreateIOProcID(id, callback, this, &callbackId);
    if (status == noErr) { started.store(true); status = AudioDeviceStart(id, callbackId); }
    if (status != noErr) { error = "Core Audio start failed (" + std::to_string(status) + "); check device and microphone permission"; stop(); return false; }
    error.clear(); return true;
}
void NativeAudio::stop() noexcept
{
    started.store(false);
    if (deviceId != kAudioObjectUnknown)
    {
        auto aliveProperty = property(kAudioDevicePropertyDeviceIsAlive);
        AudioObjectRemovePropertyListener(deviceId, &aliveProperty, devicePropertyChanged, this);
    }
    if (callbackId) { AudioDeviceStop(deviceId, callbackId); AudioDeviceDestroyIOProcID(deviceId, callbackId); }
    callbackId = nullptr; deviceId = kAudioObjectUnknown; core.reset();
}
bool NativeAudio::setGain(float gain, std::string& error)
{
    if (! started.load() || ! core) { error = "Stream stopped"; return false; }
    if (! std::isfinite(gain) || gain < 0 || gain > 1) { error = "Volume must be between 0 and 1"; return false; }
    auto next = config; next.routes[0].gain = gain;
    if (! core->publish(next, error)) return false;
    config = std::move(next); return true;
}
std::string NativeAudio::status() const
{
    if (! started.load()) return "stopped";
    if (deviceLost.load(std::memory_order_acquire)) return "device disconnected; stop and reconnect";
    if (unsupportedBuffer.load()) return "error: unsupported callback buffer layout or size";
    return callbackSeen.load() ? "callback received; count=" + std::to_string(callbacks.load())
                               : "started, waiting for callback; check microphone permission";
}
OSStatus NativeAudio::callback(AudioObjectID, const AudioTimeStamp*, const AudioBufferList* input,
                               const AudioTimeStamp*, AudioBufferList* output, const AudioTimeStamp*, void* context) noexcept
{
    auto& self = *static_cast<NativeAudio*>(context);
    if (output) for (UInt32 i = 0; i < output->mNumberBuffers; ++i)
        if (output->mBuffers[i].mData) std::memset(output->mBuffers[i].mData, 0, output->mBuffers[i].mDataByteSize);
    if (! self.started.load(std::memory_order_acquire)) return noErr;
    if (! output || output->mNumberBuffers < 2 || ! input || input->mNumberBuffers < 1)
    { self.unsupportedBuffer.store(true); return noErr; }
    const auto& l = output->mBuffers[0]; const auto& r = output->mBuffers[1];
    const auto& inL = input->mBuffers[0]; const auto& inR = input->mNumberBuffers > 1 ? input->mBuffers[1] : inL;
    const auto frames = static_cast<std::size_t>(l.mDataByteSize / sizeof(float));
    if (l.mNumberChannels != 1 || r.mNumberChannels != 1 || inL.mNumberChannels != 1 || inR.mNumberChannels != 1
        || ! l.mData || ! r.mData || l.mDataByteSize % sizeof(float) || r.mDataByteSize < l.mDataByteSize || frames > self.frameCapacity)
    { self.unsupportedBuffer.store(true); return noErr; }
    const auto available = std::min<std::size_t>(inL.mDataByteSize, inR.mDataByteSize) / sizeof(float);
    InputBlock source { 1, static_cast<const float*>(inL.mData), static_cast<const float*>(inR.mData), available };
    OutputBlock destination { 2, static_cast<float*>(l.mData), static_cast<float*>(r.mData), frames };
    if (! self.core->process(&source, 1, &destination, 1, frames)) self.unsupportedBuffer.store(true);
    self.callbackSeen.store(true, std::memory_order_release); self.callbacks.fetch_add(1, std::memory_order_relaxed);
    return noErr;
}
OSStatus NativeAudio::devicePropertyChanged(AudioObjectID device, UInt32, const AudioObjectPropertyAddress*, void* context) noexcept
{
    auto& self = *static_cast<NativeAudio*>(context);
    if (device == self.deviceId && ! alive(device))
        self.deviceLost.store(true, std::memory_order_release);
    return noErr;
}
}
