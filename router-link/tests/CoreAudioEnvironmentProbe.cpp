#include <CoreAudio/CoreAudio.h>
#include <CoreFoundation/CoreFoundation.h>

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <unistd.h>
#include <vector>

namespace {
AudioObjectPropertyAddress property(AudioObjectPropertySelector selector,
                                    AudioObjectPropertyScope scope = kAudioObjectPropertyScopeGlobal) {
    return { selector, scope, kAudioObjectPropertyElementMain };
}

std::string stringProperty(AudioObjectID device, AudioObjectPropertySelector selector) {
    auto address = property(selector); CFStringRef value = nullptr; UInt32 bytes = sizeof(value);
    if (AudioObjectGetPropertyData(device, &address, 0, nullptr, &bytes, &value) != noErr || value == nullptr) return {};
    char buffer[1024] {};
    const bool converted = CFStringGetCString(value, buffer, sizeof(buffer), kCFStringEncodingUTF8);
    CFRelease(value);
    return converted ? std::string(buffer) : std::string("<non-UTF8>");
}

std::string fourCC(UInt32 value) {
    char text[] { static_cast<char>((value >> 24) & 0xff), static_cast<char>((value >> 16) & 0xff),
                  static_cast<char>((value >> 8) & 0xff), static_cast<char>(value & 0xff), '\0' };
    for (auto& character : text) if (character == '\0') break; else if (character < 0x20 || character > 0x7e) character = '?';
    return std::string(text);
}

const char* transportLabel(UInt32 transport) {
    if (transport == kAudioDeviceTransportTypeVirtual) return "virtual";
    if (transport == kAudioDeviceTransportTypeBuiltIn) return "built-in";
    if (transport == kAudioDeviceTransportTypeAggregate) return "aggregate";
    if (transport == kAudioDeviceTransportTypeUSB) return "usb";
    if (transport == kAudioDeviceTransportTypeBluetooth) return "bluetooth";
    return "other";
}

void reportFormat(AudioDeviceID device, AudioObjectPropertyScope scope, const char* label) {
    auto address = property(kAudioDevicePropertyStreamFormat, scope); AudioStreamBasicDescription format {}; UInt32 bytes = sizeof(format);
    const auto status = AudioObjectGetPropertyData(device, &address, 0, nullptr, &bytes, &format);
    std::cout << "  " << label << ".format.status=" << status;
    if (status == noErr)
        std::cout << " sample_rate=" << std::fixed << std::setprecision(2) << format.mSampleRate
                  << " format=" << fourCC(format.mFormatID)
                  << " flags=" << format.mFormatFlags << " bits=" << format.mBitsPerChannel
                  << " channels=" << format.mChannelsPerFrame;
    std::cout << '\n';
}

void reportRates(AudioDeviceID device) {
    auto address = property(kAudioDevicePropertyNominalSampleRate); Float64 current = 0.0; UInt32 bytes = sizeof(current);
    const auto currentStatus = AudioObjectGetPropertyData(device, &address, 0, nullptr, &bytes, &current);
    std::cout << "  nominal_rate.status=" << currentStatus;
    if (currentStatus == noErr) std::cout << " current=" << std::fixed << std::setprecision(2) << current;
    std::cout << '\n';
    address = property(kAudioDevicePropertyAvailableNominalSampleRates); bytes = 0;
    const auto sizeStatus = AudioObjectGetPropertyDataSize(device, &address, 0, nullptr, &bytes);
    std::cout << "  available_rates.size.status=" << sizeStatus << " bytes=" << bytes;
    if (sizeStatus != noErr || bytes == 0 || bytes % sizeof(AudioValueRange) != 0) { std::cout << '\n'; return; }
    std::vector<AudioValueRange> ranges(bytes / sizeof(AudioValueRange));
    const auto dataStatus = AudioObjectGetPropertyData(device, &address, 0, nullptr, &bytes, ranges.data());
    std::cout << " data.status=" << dataStatus;
    if (dataStatus == noErr) for (const auto& range : ranges)
        std::cout << " [" << std::fixed << std::setprecision(2) << range.mMinimum << ',' << range.mMaximum << ']';
    std::cout << '\n';
}

void reportDirection(AudioDeviceID device, AudioObjectPropertyScope scope, const char* label) {
    auto address = property(kAudioDevicePropertyStreamConfiguration, scope); UInt32 bytes = 0;
    const auto sizeStatus = AudioObjectGetPropertyDataSize(device, &address, 0, nullptr, &bytes);
    std::cout << "  " << label << ".stream_config.size.status=" << sizeStatus << " bytes=" << bytes;
    if (sizeStatus != noErr || bytes < sizeof(AudioBufferList)) { std::cout << '\n'; return; }
    std::vector<std::uint64_t> storage((bytes + 7) / 8);
    auto* list = reinterpret_cast<AudioBufferList*>(storage.data());
    const auto dataStatus = AudioObjectGetPropertyData(device, &address, 0, nullptr, &bytes, list);
    unsigned channels = 0;
    if (dataStatus == noErr) for (UInt32 i = 0; i < list->mNumberBuffers; ++i) channels += list->mBuffers[i].mNumberChannels;
    std::cout << " data.status=" << dataStatus << " buffers=" << (dataStatus == noErr ? list->mNumberBuffers : 0)
              << " channels=" << channels << '\n';
}
}

int main() {
    const auto* sandboxContainer = std::getenv("APP_SANDBOX_CONTAINER_ID");
    std::cout << "CoreAudio environment probe (read-only)\n";
    std::cout << "pid=" << getpid() << " uid=" << getuid() << " tty=" << (isatty(STDIN_FILENO) ? "yes" : "no")
              << " app_sandbox_container=" << (sandboxContainer != nullptr ? sandboxContainer : "<unset>") << '\n';
    auto address = property(kAudioHardwarePropertyDevices); UInt32 bytes = 0;
    const auto sizeStatus = AudioObjectGetPropertyDataSize(kAudioObjectSystemObject, &address, 0, nullptr, &bytes);
    std::cout << "devices.size.status=" << sizeStatus << " bytes=" << bytes << '\n';
    if (sizeStatus != noErr) return 1;
    if (bytes % sizeof(AudioDeviceID) != 0) { std::cout << "devices.result=malformed-size\n"; return 1; }
    if (bytes == 0) {
        std::cout << "devices.data.status=not-called bytes=0 count=0\n";
        std::cout << "devices.result=zero-devices\n";
        return 0;
    }
    std::vector<AudioDeviceID> devices(bytes / sizeof(AudioDeviceID));
    UInt32 returned = bytes;
    const auto dataStatus = AudioObjectGetPropertyData(kAudioObjectSystemObject, &address, 0, nullptr, &returned,
                                                        devices.data());
    std::cout << "devices.data.status=" << dataStatus << " bytes=" << returned << " count="
              << (returned / sizeof(AudioDeviceID)) << '\n';
    if (dataStatus != noErr) return 1;
    if (returned == 0) { std::cout << "devices.result=zero-devices\n"; return 0; }
    devices.resize(returned / sizeof(AudioDeviceID));
    for (auto device : devices) {
        auto aliveAddress = property(kAudioDevicePropertyDeviceIsAlive); UInt32 alive = 0; UInt32 aliveBytes = sizeof(alive);
        const auto aliveStatus = AudioObjectGetPropertyData(device, &aliveAddress, 0, nullptr, &aliveBytes, &alive);
        auto transportAddress = property(kAudioDevicePropertyTransportType); UInt32 transport = 0; UInt32 transportBytes = sizeof(transport);
        const auto transportStatus = AudioObjectGetPropertyData(device, &transportAddress, 0, nullptr, &transportBytes, &transport);
        std::cout << "device.id=" << device << " name=" << stringProperty(device, kAudioObjectPropertyName)
                  << " uid=" << stringProperty(device, kAudioDevicePropertyDeviceUID)
                  << " alive.status=" << aliveStatus << " alive=" << alive
                  << " transport.status=" << transportStatus << " transport=" << transportLabel(transport)
                  << " transport_code=" << fourCC(transport) << '\n';
        reportDirection(device, kAudioObjectPropertyScopeInput, "input");
        reportDirection(device, kAudioObjectPropertyScopeOutput, "output");
        reportFormat(device, kAudioObjectPropertyScopeInput, "input");
        reportFormat(device, kAudioObjectPropertyScopeOutput, "output");
        reportRates(device);
    }
}
