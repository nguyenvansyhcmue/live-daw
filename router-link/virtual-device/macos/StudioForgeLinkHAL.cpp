// StudioForge Link HAL virtual-device foundation.
//
// This is an AudioServerPlugIn, hosted by coreaudiod rather than by the DAW.
// It deliberately exposes exactly one duplex Float32 stereo device. WriteMix
// connects to the bounded HalDuplexLoopback transport and ReadInput serves
// independent reader cursors. The host negotiates 44.1/48 kHz changes through
// AudioServerPlugIn's device-configuration protocol.

#include <CoreAudio/AudioServerPlugIn.h>
#include <CoreFoundation/CoreFoundation.h>
#include <mach/mach_time.h>

#include "virtual-device/macos/HalDuplexLoopback.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <cstring>
#include <mutex>

namespace
{
constexpr AudioObjectID kDevice = 2;
constexpr AudioObjectID kInputStream = 3;
constexpr AudioObjectID kOutputStream = 4;
const CFStringRef kDeviceUID = CFSTR("com.studioforge.link.virtual-duplex.v1");
const CFStringRef kModelUID = CFSTR("com.studioforge.link.virtual-duplex.model.v1");
const CFStringRef kDeviceName = CFSTR("StudioForge Link");
const CFStringRef kManufacturer = CFSTR("StudioForge");
constexpr UInt32 kChannels = 2;
constexpr UInt32 kNominalBufferFrames = 256;
constexpr Float64 kDefaultRate = 48000.0;
constexpr std::array<Float64, 2> kSupportedRates { 44100.0, 48000.0 };

std::atomic<UInt32> referenceCount { 1 };
std::atomic<UInt32> ioClientCount { 0 };
// StartIO and StopIO are lifecycle calls, not DoIOOperation callbacks. Keep
// their bookkeeping serialized without putting a lock in the audio path.
std::mutex ioLifecycleMutex;
std::array<UInt32, 64> activeIOClients {};
std::atomic<UInt64> zeroHostTime { 0 };
std::atomic<Float64> hostTicksPerSecond { 0.0 };
std::atomic<Float64> sampleRate { kDefaultRate };
std::atomic<Float64> pendingSampleRate { 0.0 };
std::atomic<UInt64> underrunCount { 0 };
studioforge::link::macos::HalDuplexLoopback loopback { 1u << 16 };
AudioServerPlugInHostRef host = nullptr;

bool isSupportedRate(const Float64 rate) noexcept
{
    return std::find(kSupportedRates.begin(), kSupportedRates.end(), rate) != kSupportedRates.end();
}

AudioStreamBasicDescription makeFormat(const Float64 rate) noexcept
{
    AudioStreamBasicDescription result {};
    result.mSampleRate = rate;
    result.mFormatID = kAudioFormatLinearPCM;
    result.mFormatFlags = kAudioFormatFlagIsFloat | kAudioFormatFlagIsPacked;
    result.mBytesPerPacket = kChannels * sizeof(Float32);
    result.mFramesPerPacket = 1;
    result.mBytesPerFrame = kChannels * sizeof(Float32);
    result.mChannelsPerFrame = kChannels;
    result.mBitsPerChannel = 32;
    return result;
}

bool isGlobal(const AudioObjectPropertyAddress* address) noexcept
{
    return address != nullptr && address->mScope == kAudioObjectPropertyScopeGlobal;
}

bool isStreamScope(const AudioObjectPropertyAddress* address, const bool input) noexcept
{
    return address != nullptr && (address->mScope == kAudioObjectPropertyScopeGlobal
        || address->mScope == (input ? kAudioObjectPropertyScopeInput : kAudioObjectPropertyScopeOutput));
}

template <typename T>
OSStatus put(const T& value, const UInt32 dataSize, UInt32* outDataSize, void* outData) noexcept
{
    if (outData == nullptr || outDataSize == nullptr || dataSize < sizeof(T))
        return kAudioHardwareBadPropertySizeError;
    std::memcpy(outData, &value, sizeof(T));
    *outDataSize = sizeof(T);
    return noErr;
}

OSStatus putCF(CFTypeRef value, const UInt32 dataSize, UInt32* outDataSize, void* outData) noexcept
{
    if (outData == nullptr || outDataSize == nullptr || dataSize < sizeof(CFTypeRef))
        return kAudioHardwareBadPropertySizeError;
    CFRetain(value);
    std::memcpy(outData, &value, sizeof(value));
    *outDataSize = sizeof(value);
    return noErr;
}

OSStatus badProperty() noexcept { return kAudioHardwareUnknownPropertyError; }

bool hasPluginProperty(const AudioObjectPropertyAddress& a) noexcept
{
    return isGlobal(&a) && (a.mSelector == kAudioObjectPropertyBaseClass
        || a.mSelector == kAudioObjectPropertyClass || a.mSelector == kAudioObjectPropertyOwner
        || a.mSelector == kAudioObjectPropertyManufacturer || a.mSelector == kAudioObjectPropertyOwnedObjects
        || a.mSelector == kAudioPlugInPropertyDeviceList || a.mSelector == kAudioPlugInPropertyTranslateUIDToDevice);
}

bool hasDeviceProperty(const AudioObjectPropertyAddress& a) noexcept
{
    if (! isGlobal(&a) && a.mSelector != kAudioDevicePropertyStreams) return false;
    switch (a.mSelector)
    {
        case kAudioObjectPropertyBaseClass: case kAudioObjectPropertyClass: case kAudioObjectPropertyOwner:
        case kAudioObjectPropertyName: case kAudioObjectPropertyManufacturer: case kAudioDevicePropertyModelUID:
        case kAudioDevicePropertyDeviceUID: case kAudioDevicePropertyTransportType: case kAudioDevicePropertyRelatedDevices:
        case kAudioDevicePropertyClockDomain: case kAudioDevicePropertyDeviceIsAlive: case kAudioDevicePropertyDeviceIsRunning:
        case kAudioDevicePropertyDeviceCanBeDefaultDevice: case kAudioDevicePropertyDeviceCanBeDefaultSystemDevice:
        case kAudioDevicePropertyLatency: case kAudioDevicePropertySafetyOffset: case kAudioDevicePropertyStreams:
        case kAudioDevicePropertyNominalSampleRate: case kAudioDevicePropertyAvailableNominalSampleRates:
        case kAudioDevicePropertyPreferredChannelsForStereo: case kAudioObjectPropertyOwnedObjects:
            return true;
        default: return false;
    }
}

bool hasStreamProperty(const AudioObjectPropertyAddress& a, const bool input) noexcept
{
    if (! isStreamScope(&a, input)) return false;
    switch (a.mSelector)
    {
        case kAudioObjectPropertyBaseClass: case kAudioObjectPropertyClass: case kAudioObjectPropertyOwner:
        case kAudioObjectPropertyName: case kAudioStreamPropertyIsActive: case kAudioStreamPropertyDirection:
        case kAudioStreamPropertyTerminalType: case kAudioStreamPropertyStartingChannel: case kAudioStreamPropertyLatency:
        case kAudioStreamPropertyVirtualFormat: case kAudioStreamPropertyPhysicalFormat:
        case kAudioStreamPropertyAvailableVirtualFormats: case kAudioStreamPropertyAvailablePhysicalFormats:
            return true;
        default: return false;
    }
}

Boolean hasProperty(AudioServerPlugInDriverRef, const AudioObjectID object, pid_t,
                    const AudioObjectPropertyAddress* address)
{
    if (address == nullptr) return false;
    if (object == kAudioObjectPlugInObject) return hasPluginProperty(*address);
    if (object == kDevice) return hasDeviceProperty(*address);
    if (object == kInputStream) return hasStreamProperty(*address, true);
    if (object == kOutputStream) return hasStreamProperty(*address, false);
    return false;
}

OSStatus isSettable(AudioServerPlugInDriverRef, AudioObjectID object, pid_t,
                    const AudioObjectPropertyAddress* address, Boolean* result)
{
    if (result == nullptr || !hasProperty(nullptr, object, 0, address)) return badProperty();
    *result = (object == kDevice && address->mSelector == kAudioDevicePropertyNominalSampleRate)
        || ((object == kInputStream || object == kOutputStream)
            && (address->mSelector == kAudioStreamPropertyVirtualFormat
                || address->mSelector == kAudioStreamPropertyPhysicalFormat));
    return noErr;
}

OSStatus propertySize(AudioServerPlugInDriverRef, const AudioObjectID object, pid_t,
                      const AudioObjectPropertyAddress* a, UInt32, const void*, UInt32* size)
{
    if (a == nullptr || size == nullptr || !hasProperty(nullptr, object, 0, a)) return badProperty();
    if (object == kAudioObjectPlugInObject)
    {
        if (a->mSelector == kAudioObjectPropertyOwnedObjects || a->mSelector == kAudioPlugInPropertyDeviceList) *size = sizeof(AudioObjectID);
        else if (a->mSelector == kAudioPlugInPropertyTranslateUIDToDevice) *size = sizeof(AudioObjectID);
        else if (a->mSelector == kAudioObjectPropertyManufacturer) *size = sizeof(CFStringRef);
        else *size = sizeof(AudioClassID);
        return noErr;
    }
    if (object == kDevice)
    {
        if (a->mSelector == kAudioObjectPropertyOwnedObjects) *size = 2 * sizeof(AudioObjectID);
        else if (a->mSelector == kAudioDevicePropertyRelatedDevices) *size = sizeof(AudioObjectID);
        else if (a->mSelector == kAudioDevicePropertyStreams) *size = sizeof(AudioObjectID);
        else if (a->mSelector == kAudioDevicePropertyAvailableNominalSampleRates) *size = kSupportedRates.size() * sizeof(AudioValueRange);
        else if (a->mSelector == kAudioDevicePropertyPreferredChannelsForStereo) *size = 2 * sizeof(UInt32);
        else if (a->mSelector == kAudioObjectPropertyName || a->mSelector == kAudioObjectPropertyManufacturer
                 || a->mSelector == kAudioDevicePropertyModelUID || a->mSelector == kAudioDevicePropertyDeviceUID) *size = sizeof(CFStringRef);
        else if (a->mSelector == kAudioDevicePropertyNominalSampleRate) *size = sizeof(Float64);
        else *size = sizeof(UInt32);
        return noErr;
    }
    if (a->mSelector == kAudioObjectPropertyName) *size = sizeof(CFStringRef);
    else if (a->mSelector == kAudioStreamPropertyVirtualFormat || a->mSelector == kAudioStreamPropertyPhysicalFormat) *size = sizeof(AudioStreamBasicDescription);
    else if (a->mSelector == kAudioStreamPropertyAvailableVirtualFormats || a->mSelector == kAudioStreamPropertyAvailablePhysicalFormats) *size = kSupportedRates.size() * sizeof(AudioStreamRangedDescription);
    else *size = sizeof(UInt32);
    return noErr;
}

OSStatus propertyData(AudioServerPlugInDriverRef, const AudioObjectID object, pid_t,
                      const AudioObjectPropertyAddress* a, const UInt32 qualifierSize, const void* qualifier,
                      const UInt32 dataSize, UInt32* outSize, void* outData)
{
    if (a == nullptr || !hasProperty(nullptr, object, 0, a)) return badProperty();
    if (object == kAudioObjectPlugInObject)
    {
        switch (a->mSelector)
        {
            case kAudioObjectPropertyBaseClass: { const AudioClassID x = kAudioObjectClassID; return put(x, dataSize, outSize, outData); }
            case kAudioObjectPropertyClass: { const AudioClassID x = kAudioPlugInClassID; return put(x, dataSize, outSize, outData); }
            case kAudioObjectPropertyOwner: { const AudioObjectID x = kAudioObjectUnknown; return put(x, dataSize, outSize, outData); }
            case kAudioObjectPropertyManufacturer: return putCF(kManufacturer, dataSize, outSize, outData);
            case kAudioObjectPropertyOwnedObjects: case kAudioPlugInPropertyDeviceList: { const AudioObjectID x = kDevice; return put(x, dataSize, outSize, outData); }
            case kAudioPlugInPropertyTranslateUIDToDevice:
                if (qualifier == nullptr || qualifierSize != sizeof(CFStringRef)) return kAudioHardwareBadPropertySizeError;
                { const auto candidate = *static_cast<const CFStringRef*>(qualifier); const AudioObjectID x = (candidate != nullptr && CFEqual(candidate, kDeviceUID)) ? kDevice : kAudioObjectUnknown; return put(x, dataSize, outSize, outData); }
            default: return badProperty();
        }
    }
    if (object == kDevice)
    {
        switch (a->mSelector)
        {
            case kAudioObjectPropertyBaseClass: { const AudioClassID x = kAudioObjectClassID; return put(x, dataSize, outSize, outData); }
            case kAudioObjectPropertyClass: { const AudioClassID x = kAudioDeviceClassID; return put(x, dataSize, outSize, outData); }
            case kAudioObjectPropertyOwner: { const AudioObjectID x = kAudioObjectPlugInObject; return put(x, dataSize, outSize, outData); }
            case kAudioObjectPropertyName: return putCF(kDeviceName, dataSize, outSize, outData);
            case kAudioObjectPropertyManufacturer: return putCF(kManufacturer, dataSize, outSize, outData);
            case kAudioDevicePropertyModelUID: return putCF(kModelUID, dataSize, outSize, outData);
            case kAudioDevicePropertyDeviceUID: return putCF(kDeviceUID, dataSize, outSize, outData);
            case kAudioObjectPropertyOwnedObjects:
                if (dataSize < 2 * sizeof(AudioObjectID) || outData == nullptr || outSize == nullptr) return kAudioHardwareBadPropertySizeError;
                static_cast<AudioObjectID*>(outData)[0] = kInputStream; static_cast<AudioObjectID*>(outData)[1] = kOutputStream; *outSize = 2 * sizeof(AudioObjectID); return noErr;
            case kAudioDevicePropertyTransportType: { const UInt32 x = kAudioDeviceTransportTypeVirtual; return put(x, dataSize, outSize, outData); }
            case kAudioDevicePropertyRelatedDevices: { const AudioObjectID x = kDevice; return put(x, dataSize, outSize, outData); }
            case kAudioDevicePropertyClockDomain: { const UInt32 x = 0; return put(x, dataSize, outSize, outData); }
            case kAudioDevicePropertyDeviceIsAlive: { const UInt32 x = 1; return put(x, dataSize, outSize, outData); }
            case kAudioDevicePropertyDeviceIsRunning: { const UInt32 x = ioClientCount.load(std::memory_order_acquire) != 0; return put(x, dataSize, outSize, outData); }
            case kAudioDevicePropertyDeviceCanBeDefaultDevice: case kAudioDevicePropertyDeviceCanBeDefaultSystemDevice: { const UInt32 x = 0; return put(x, dataSize, outSize, outData); }
            case kAudioDevicePropertyLatency: case kAudioDevicePropertySafetyOffset: { const UInt32 x = 0; return put(x, dataSize, outSize, outData); }
            case kAudioDevicePropertyStreams: { const AudioObjectID x = a->mScope == kAudioObjectPropertyScopeInput ? kInputStream : kOutputStream; return put(x, dataSize, outSize, outData); }
            case kAudioDevicePropertyNominalSampleRate: { const auto x = sampleRate.load(std::memory_order_relaxed); return put(x, dataSize, outSize, outData); }
            case kAudioDevicePropertyAvailableNominalSampleRates:
                if (dataSize < kSupportedRates.size() * sizeof(AudioValueRange) || outData == nullptr || outSize == nullptr) return kAudioHardwareBadPropertySizeError;
                for (std::size_t i = 0; i < kSupportedRates.size(); ++i)
                    static_cast<AudioValueRange*>(outData)[i] = { kSupportedRates[i], kSupportedRates[i] };
                *outSize = static_cast<UInt32>(kSupportedRates.size() * sizeof(AudioValueRange)); return noErr;
            case kAudioDevicePropertyPreferredChannelsForStereo:
                if (dataSize < 2 * sizeof(UInt32) || outData == nullptr || outSize == nullptr) return kAudioHardwareBadPropertySizeError;
                static_cast<UInt32*>(outData)[0] = 1; static_cast<UInt32*>(outData)[1] = 2; *outSize = 2 * sizeof(UInt32); return noErr;
            default: return badProperty();
        }
    }
    const bool input = object == kInputStream;
    switch (a->mSelector)
    {
        case kAudioObjectPropertyBaseClass: { const AudioClassID x = kAudioObjectClassID; return put(x, dataSize, outSize, outData); }
        case kAudioObjectPropertyClass: { const AudioClassID x = kAudioStreamClassID; return put(x, dataSize, outSize, outData); }
        case kAudioObjectPropertyOwner: { const AudioObjectID x = kDevice; return put(x, dataSize, outSize, outData); }
        case kAudioObjectPropertyName: return putCF(input ? CFSTR("StudioForge Link Input") : CFSTR("StudioForge Link Output"), dataSize, outSize, outData);
        case kAudioStreamPropertyIsActive: { const UInt32 x = 1; return put(x, dataSize, outSize, outData); }
        case kAudioStreamPropertyDirection: { const UInt32 x = input ? 1 : 0; return put(x, dataSize, outSize, outData); }
        case kAudioStreamPropertyTerminalType: { const UInt32 x = input ? kAudioStreamTerminalTypeMicrophone : kAudioStreamTerminalTypeSpeaker; return put(x, dataSize, outSize, outData); }
        case kAudioStreamPropertyStartingChannel: { const UInt32 x = 1; return put(x, dataSize, outSize, outData); }
        case kAudioStreamPropertyLatency: { const UInt32 x = 0; return put(x, dataSize, outSize, outData); }
        case kAudioStreamPropertyVirtualFormat: case kAudioStreamPropertyPhysicalFormat: { const auto x = makeFormat(sampleRate.load(std::memory_order_relaxed)); return put(x, dataSize, outSize, outData); }
        case kAudioStreamPropertyAvailableVirtualFormats: case kAudioStreamPropertyAvailablePhysicalFormats:
            if (dataSize < kSupportedRates.size() * sizeof(AudioStreamRangedDescription) || outData == nullptr || outSize == nullptr) return kAudioHardwareBadPropertySizeError;
            for (std::size_t i = 0; i < kSupportedRates.size(); ++i)
                static_cast<AudioStreamRangedDescription*>(outData)[i] = { makeFormat(kSupportedRates[i]), { kSupportedRates[i], kSupportedRates[i] } };
            *outSize = static_cast<UInt32>(kSupportedRates.size() * sizeof(AudioStreamRangedDescription)); return noErr;
        default: return badProperty();
    }
}

OSStatus requestSampleRateChange(const Float64 requestedRate)
{
    if (!isSupportedRate(requestedRate)) return kAudioDeviceUnsupportedFormatError;
    if (requestedRate == sampleRate.load(std::memory_order_acquire)) return noErr;
    if (host == nullptr || host->RequestDeviceConfigurationChange == nullptr)
        return kAudioHardwareIllegalOperationError;

    pendingSampleRate.store(requestedRate, std::memory_order_release);
    const auto status = host->RequestDeviceConfigurationChange(host, kDevice,
                                                                static_cast<UInt64>(requestedRate), nullptr);
    if (status != noErr) pendingSampleRate.store(0.0, std::memory_order_release);
    return status;
}

OSStatus setProperty(AudioServerPlugInDriverRef, const AudioObjectID object, pid_t,
                     const AudioObjectPropertyAddress* address, UInt32, const void*,
                     const UInt32 dataSize, const void* data)
{
    if (address == nullptr || !hasProperty(nullptr, object, 0, address)) return badProperty();
    if (data == nullptr) return kAudioHardwareIllegalOperationError;

    if (object == kDevice && address->mSelector == kAudioDevicePropertyNominalSampleRate)
    {
        if (dataSize != sizeof(Float64)) return kAudioHardwareBadPropertySizeError;
        return requestSampleRateChange(*static_cast<const Float64*>(data));
    }

    if ((object == kInputStream || object == kOutputStream)
        && (address->mSelector == kAudioStreamPropertyVirtualFormat
            || address->mSelector == kAudioStreamPropertyPhysicalFormat))
    {
        if (dataSize != sizeof(AudioStreamBasicDescription)) return kAudioHardwareBadPropertySizeError;
        const auto& format = *static_cast<const AudioStreamBasicDescription*>(data);
        const auto expected = makeFormat(format.mSampleRate);
        if (std::memcmp(&format, &expected, sizeof(format)) != 0)
            return kAudioDeviceUnsupportedFormatError;
        return requestSampleRateChange(format.mSampleRate);
    }
    return kAudioHardwareUnsupportedOperationError;
}
HRESULT queryInterface(void*, REFIID uuid, LPVOID* result);
ULONG addRef(void*) { return referenceCount.fetch_add(1, std::memory_order_relaxed) + 1; }
ULONG release(void*)
{
    auto n = referenceCount.load(std::memory_order_relaxed);
    while (n > 1 && !referenceCount.compare_exchange_weak(n, n - 1, std::memory_order_relaxed)) {}
    return n > 1 ? n - 1 : 1;
}
OSStatus initialize(AudioServerPlugInDriverRef, AudioServerPlugInHostRef inHost)
{
    host = inHost;
    if (inHost == nullptr) return kAudioHardwareIllegalOperationError;
    mach_timebase_info_data_t timebase {};
    mach_timebase_info(&timebase);
    if (timebase.numer == 0 || timebase.denom == 0) return kAudioHardwareUnspecifiedError;
    hostTicksPerSecond.store(1.0e9 * static_cast<Float64>(timebase.denom) / static_cast<Float64>(timebase.numer), std::memory_order_release);
    return noErr;
}
OSStatus noDynamicDevice(AudioServerPlugInDriverRef, CFDictionaryRef, const AudioServerPlugInClientInfo*, AudioObjectID*) { return kAudioHardwareUnsupportedOperationError; }
OSStatus destroyDevice(AudioServerPlugInDriverRef, AudioObjectID) { return kAudioHardwareUnsupportedOperationError; }
OSStatus addClient(AudioServerPlugInDriverRef, AudioObjectID object, const AudioServerPlugInClientInfo*)
{
    return object == kDevice ? static_cast<OSStatus>(noErr) : static_cast<OSStatus>(kAudioHardwareBadObjectError);
}
OSStatus removeClient(AudioServerPlugInDriverRef, AudioObjectID object, const AudioServerPlugInClientInfo* client)
{
    if (object != kDevice) return kAudioHardwareBadObjectError;
    if (client != nullptr) { loopback.removeClient(client->mClientID); loopback.disconnectWriter(client->mClientID); }
    return noErr;
}
OSStatus configChange(AudioServerPlugInDriverRef, const AudioObjectID object, const UInt64 action, void*)
{
    if (object != kDevice) return kAudioHardwareBadObjectError;
    const auto requestedRate = static_cast<Float64>(action);
    if (!isSupportedRate(requestedRate)
        || pendingSampleRate.load(std::memory_order_acquire) != requestedRate)
        return kAudioHardwareIllegalOperationError;

    const std::lock_guard<std::mutex> lock(ioLifecycleMutex);
    if (ioClientCount.load(std::memory_order_acquire) != 0)
        return kAudioHardwareIllegalOperationError;
    sampleRate.store(requestedRate, std::memory_order_release);
    pendingSampleRate.store(0.0, std::memory_order_release);
    loopback.resetWhenStopped();
    zeroHostTime.store(mach_absolute_time(), std::memory_order_release);
    return noErr;
}

OSStatus abortConfig(AudioServerPlugInDriverRef, const AudioObjectID object, const UInt64 action, void*)
{
    if (object != kDevice) return kAudioHardwareBadObjectError;
    const auto requestedRate = static_cast<Float64>(action);
    if (pendingSampleRate.load(std::memory_order_acquire) == requestedRate)
        pendingSampleRate.store(0.0, std::memory_order_release);
    return noErr;
}
OSStatus startIO(AudioServerPlugInDriverRef, AudioObjectID object, UInt32 client)
{
    if (object != kDevice) return kAudioHardwareBadObjectError;
    if (client == kAudioServerPlugInHostClientID) return kAudioHardwareIllegalOperationError;
    const std::lock_guard<std::mutex> lock(ioLifecycleMutex);
    if (std::find(activeIOClients.begin(), activeIOClients.end(), client) != activeIOClients.end()) return noErr;
    const auto slot = std::find(activeIOClients.begin(), activeIOClients.end(), 0);
    if (slot == activeIOClients.end()) return kAudioHardwareUnspecifiedError;
    if (ioClientCount.load(std::memory_order_relaxed) == 0)
    {
        loopback.resetWhenStopped();
        zeroHostTime.store(mach_absolute_time(), std::memory_order_release);
    }
    *slot = client;
    ioClientCount.fetch_add(1, std::memory_order_release);
    return noErr;
}
OSStatus stopIO(AudioServerPlugInDriverRef, AudioObjectID object, UInt32 client)
{
    if (object != kDevice) return kAudioHardwareBadObjectError;
    const std::lock_guard<std::mutex> lock(ioLifecycleMutex);
    const auto slot = std::find(activeIOClients.begin(), activeIOClients.end(), client);
    if (client == 0 || slot == activeIOClients.end()) return noErr;
    *slot = 0;
    loopback.removeClient(client);
    loopback.disconnectWriter(client);
    if (ioClientCount.fetch_sub(1, std::memory_order_acq_rel) == 1) loopback.resetWhenStopped();
    return noErr;
}
OSStatus zeroTimestamp(AudioServerPlugInDriverRef, AudioObjectID object, UInt32, Float64* sample, UInt64* hostTime, UInt64* seed)
{
    if (object != kDevice || sample == nullptr || hostTime == nullptr || seed == nullptr) return kAudioHardwareIllegalOperationError;
    const auto now = mach_absolute_time();
    const auto anchor = zeroHostTime.load(std::memory_order_acquire);
    const auto ticks = hostTicksPerSecond.load(std::memory_order_acquire);
    *hostTime = now;
    *sample = (anchor != 0 && ticks > 0.0)
        ? static_cast<Float64>(now - anchor) * sampleRate.load(std::memory_order_relaxed) / ticks : 0.0;
    *seed = 1;
    return noErr;
}
OSStatus willDo(AudioServerPlugInDriverRef, AudioObjectID object, UInt32, UInt32 op, Boolean* will, Boolean* inplace)
{
    if (object != kDevice || will == nullptr || inplace == nullptr) return kAudioHardwareIllegalOperationError;
    *will = op == kAudioServerPlugInIOOperationReadInput || op == kAudioServerPlugInIOOperationWriteMix;
    *inplace = true; return noErr;
}
OSStatus beginIO(AudioServerPlugInDriverRef, AudioObjectID object, UInt32, UInt32, UInt32, const AudioServerPlugInIOCycleInfo*) { return object == kDevice ? static_cast<OSStatus>(noErr) : static_cast<OSStatus>(kAudioHardwareBadObjectError); }
OSStatus doIO(AudioServerPlugInDriverRef, AudioObjectID object, AudioObjectID stream, UInt32 client, UInt32 op, UInt32 frames, const AudioServerPlugInIOCycleInfo*, void* main, void*)
{
    if (object != kDevice || (stream != kInputStream && stream != kOutputStream)) return kAudioHardwareBadObjectError;
    if (op == kAudioServerPlugInIOOperationReadInput && stream == kInputStream)
    {
        if (main != nullptr && loopback.read(client, static_cast<float*>(main), frames) != frames)
            underrunCount.fetch_add(1, std::memory_order_relaxed);
    }
    else if (op == kAudioServerPlugInIOOperationWriteMix && stream == kOutputStream && main != nullptr)
        static_cast<void>(loopback.write(client, static_cast<const float*>(main), frames));
    return noErr;
}
OSStatus endIO(AudioServerPlugInDriverRef, AudioObjectID object, UInt32, UInt32, UInt32, const AudioServerPlugInIOCycleInfo*) { return object == kDevice ? static_cast<OSStatus>(noErr) : static_cast<OSStatus>(kAudioHardwareBadObjectError); }

AudioServerPlugInDriverInterface gInterface {
    nullptr, queryInterface, addRef, release, initialize, noDynamicDevice, destroyDevice, addClient, removeClient,
    configChange, abortConfig, hasProperty, isSettable, propertySize, propertyData, setProperty,
    startIO, stopIO, zeroTimestamp, willDo, beginIO, doIO, endIO
};
AudioServerPlugInDriverInterface* gInterfacePointer = &gInterface;
AudioServerPlugInDriverRef gDriver = &gInterfacePointer;

HRESULT queryInterface(void*, REFIID uuid, LPVOID* result)
{
    if (result == nullptr) return E_POINTER;
    *result = nullptr;
    auto requested = CFUUIDCreateFromUUIDBytes(kCFAllocatorDefault, uuid);
    const bool supported = requested != nullptr && (CFEqual(requested, IUnknownUUID) || CFEqual(requested, kAudioServerPlugInDriverInterfaceUUID));
    if (requested != nullptr) CFRelease(requested);
    if (! supported) return E_NOINTERFACE;
    *result = gDriver;
    addRef(nullptr);
    return S_OK;
}
}

extern "C" void* StudioForgeLinkHALFactory(CFAllocatorRef, CFUUIDRef typeUUID)
{
    if (typeUUID == nullptr || !CFEqual(typeUUID, kAudioServerPlugInTypeUUID)) return nullptr;
    addRef(nullptr);
    return gDriver;
}
