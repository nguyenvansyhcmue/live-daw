#include <CoreAudio/AudioServerPlugIn.h>
#include <CoreFoundation/CoreFoundation.h>
#include <dlfcn.h>

#include <array>
#include <cassert>

using Factory = void* (*)(CFAllocatorRef, CFUUIDRef);

namespace
{
UInt64 requestedConfigurationAction = 0;

OSStatus propertiesChanged(AudioServerPlugInHostRef, AudioObjectID, UInt32,
                           const AudioObjectPropertyAddress*) { return noErr; }
OSStatus copyFromStorage(AudioServerPlugInHostRef, CFStringRef, CFPropertyListRef*)
{ return kAudioHardwareUnsupportedOperationError; }
OSStatus writeToStorage(AudioServerPlugInHostRef, CFStringRef, CFPropertyListRef)
{ return kAudioHardwareUnsupportedOperationError; }
OSStatus deleteFromStorage(AudioServerPlugInHostRef, CFStringRef)
{ return kAudioHardwareUnsupportedOperationError; }
OSStatus requestConfigurationChange(AudioServerPlugInHostRef, AudioObjectID device, UInt64 action, void*)
{
    assert(device == 2);
    requestedConfigurationAction = action;
    return noErr;
}

AudioServerPlugInHostInterface testHost {
    propertiesChanged, copyFromStorage, writeToStorage, deleteFromStorage, requestConfigurationChange
};
}

int main()
{
    void* bundle = dlopen(STUDIOFORGE_LINK_HAL_BINARY, RTLD_NOW | RTLD_LOCAL);
    assert(bundle != nullptr);
    const auto factory = reinterpret_cast<Factory>(dlsym(bundle, "StudioForgeLinkHALFactory"));
    assert(factory != nullptr);
    auto driver = static_cast<AudioServerPlugInDriverRef>(factory(kCFAllocatorDefault, kAudioServerPlugInTypeUUID));
    assert(driver != nullptr && *driver != nullptr);
    assert((*driver)->Initialize(driver, &testHost) == noErr);

    AudioObjectPropertyAddress address { kAudioPlugInPropertyDeviceList, kAudioObjectPropertyScopeGlobal,
                                         kAudioObjectPropertyElementMain };
    assert((*driver)->HasProperty(driver, kAudioObjectPlugInObject, 0, &address));
    AudioObjectID device = kAudioObjectUnknown;
    UInt32 actual = 0;
    assert((*driver)->GetPropertyData(driver, kAudioObjectPlugInObject, 0, &address, 0, nullptr,
                                      sizeof(device), &actual, &device) == noErr);
    assert(actual == sizeof(device) && device == 2);

    address = { kAudioDevicePropertyDeviceUID, kAudioObjectPropertyScopeGlobal, kAudioObjectPropertyElementMain };
    CFStringRef uid = nullptr;
    assert((*driver)->GetPropertyData(driver, device, 0, &address, 0, nullptr, sizeof(uid), &actual, &uid) == noErr);
    assert(uid != nullptr);
    assert(CFEqual(uid, CFSTR("com.studioforge.link.virtual-duplex.v1")));
    CFRelease(uid);

    address = { kAudioStreamPropertyVirtualFormat, kAudioObjectPropertyScopeInput, kAudioObjectPropertyElementMain };
    AudioStreamBasicDescription format {};
    assert((*driver)->GetPropertyData(driver, 3, 0, &address, 0, nullptr, sizeof(format), &actual, &format) == noErr);
    assert(format.mSampleRate == 48000.0 && format.mChannelsPerFrame == 2 && format.mBitsPerChannel == 32);

    // Both common music rates are advertised, and changes travel through the
    // host's configuration-change handshake rather than mutating live IO.
    address = { kAudioDevicePropertyAvailableNominalSampleRates, kAudioObjectPropertyScopeGlobal,
                kAudioObjectPropertyElementMain };
    UInt32 propertySize = 0;
    Boolean writable = false;
    assert((*driver)->GetPropertyDataSize(driver, device, 0, &address, 0, nullptr, &propertySize) == noErr);
    assert(propertySize == 2 * sizeof(AudioValueRange));
    std::array<AudioValueRange, 2> rates {};
    assert((*driver)->GetPropertyData(driver, device, 0, &address, 0, nullptr,
                                      sizeof(rates), &actual, rates.data()) == noErr);
    assert(rates[0].mMinimum == 44100.0 && rates[1].mMaximum == 48000.0);

    address = { kAudioDevicePropertyNominalSampleRate, kAudioObjectPropertyScopeGlobal,
                kAudioObjectPropertyElementMain };
    assert((*driver)->IsPropertySettable(driver, device, 0, &address, &writable) == noErr && writable);
    const Float64 newRate = 44100.0;
    assert((*driver)->SetPropertyData(driver, device, 0, &address, 0, nullptr,
                                      sizeof(newRate), &newRate) == noErr);
    assert(requestedConfigurationAction == 44100);
    assert((*driver)->PerformDeviceConfigurationChange(driver, device,
                                                        requestedConfigurationAction, nullptr) == noErr);
    Float64 currentRate = 0.0;
    assert((*driver)->GetPropertyData(driver, device, 0, &address, 0, nullptr,
                                      sizeof(currentRate), &actual, &currentRate) == noErr);
    assert(currentRate == 44100.0);

    const Float64 unsupportedRate = 96000.0;
    assert((*driver)->SetPropertyData(driver, device, 0, &address, 0, nullptr,
                                      sizeof(unsupportedRate), &unsupportedRate)
           == kAudioDeviceUnsupportedFormatError);

    assert((*driver)->StartIO(driver, device, 17) == noErr);
    std::array<float, 10> capture;
    capture.fill(1.0f);
    AudioServerPlugInIOCycleInfo cycle {};
    assert((*driver)->DoIOOperation(driver, device, 3, 17, kAudioServerPlugInIOOperationReadInput,
                                    5, &cycle, capture.data(), nullptr) == noErr);
    for (const auto value : capture) assert(value == 0.0f);
    const std::array<float, 6> written { 0.25f, -0.25f, 0.5f, -0.5f, 0.75f, -0.75f };
    assert((*driver)->DoIOOperation(driver, device, 4, 17, kAudioServerPlugInIOOperationWriteMix,
                                    3, &cycle, const_cast<float*>(written.data()), nullptr) == noErr);
    std::array<float, 6> looped {};
    assert((*driver)->DoIOOperation(driver, device, 3, 17, kAudioServerPlugInIOOperationReadInput,
                                    3, &cycle, looped.data(), nullptr) == noErr);
    for (unsigned i = 0; i < written.size(); ++i) assert(looped[i] == written[i]);
    assert((*driver)->StopIO(driver, device, 17) == noErr);
    assert((*driver)->StopIO(driver, device, 17) == noErr);

    // Duplicate stop for one client must not stop another active client.
    assert((*driver)->StartIO(driver, device, 17) == noErr);
    assert((*driver)->StartIO(driver, device, 18) == noErr);
    assert((*driver)->StopIO(driver, device, 17) == noErr);
    assert((*driver)->StopIO(driver, device, 17) == noErr);
    address = { kAudioDevicePropertyDeviceIsRunning, kAudioObjectPropertyScopeGlobal,
                kAudioObjectPropertyElementMain };
    UInt32 running = 0;
    assert((*driver)->GetPropertyData(driver, device, 0, &address, 0, nullptr,
                                      sizeof(running), &actual, &running) == noErr);
    assert(running == 1);
    assert((*driver)->StopIO(driver, device, 18) == noErr);

    // Fixed lifecycle capacity must reject the 65th distinct client and
    // become available again after an existing client stops.
    for (UInt32 client = 100; client < 164; ++client)
        assert((*driver)->StartIO(driver, device, client) == noErr);
    assert((*driver)->StartIO(driver, device, 164) != noErr);
    assert((*driver)->StopIO(driver, device, 100) == noErr);
    assert((*driver)->StartIO(driver, device, 164) == noErr);
    for (UInt32 client = 101; client <= 164; ++client)
        assert((*driver)->StopIO(driver, device, client) == noErr);
    dlclose(bundle);
}
