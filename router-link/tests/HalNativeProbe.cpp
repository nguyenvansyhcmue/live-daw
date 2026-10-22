#include <CoreAudio/CoreAudio.h>
#include <CoreFoundation/CoreFoundation.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

// Run as two separate processes, one writer and one reader. This deliberately
// measures the device's exposed sample timeline, not the HAL's private FIFO.
namespace {
constexpr std::int64_t period = 1 << 20;
constexpr float scale = static_cast<float>(1 << 21);
struct Sample { float left, right; double inputTime; bool hasTime; };
struct Context {
    bool writer;
    std::vector<Sample> captured;
    std::size_t used = 0;
    std::atomic<unsigned> callbacks { 0 }, badLayout { 0 }, noTime { 0 }, truncated { 0 };
};

bool stereo(const AudioBufferList* list, std::size_t& frames) {
    if (!list) return false;
    if (list->mNumberBuffers == 1) {
        const auto& b = list->mBuffers[0];
        if (!b.mData || b.mNumberChannels != 2 || b.mDataByteSize % (2 * sizeof(float))) return false;
        frames = b.mDataByteSize / (2 * sizeof(float)); return true;
    }
    if (list->mNumberBuffers != 2) return false;
    const auto& l = list->mBuffers[0]; const auto& r = list->mBuffers[1];
    if (!l.mData || !r.mData || l.mNumberChannels != 1 || r.mNumberChannels != 1 ||
        l.mDataByteSize != r.mDataByteSize || l.mDataByteSize % sizeof(float)) return false;
    frames = l.mDataByteSize / sizeof(float); return true;
}
float get(const AudioBufferList* list, std::size_t frame, unsigned channel) {
    return list->mNumberBuffers == 1 ? static_cast<const float*>(list->mBuffers[0].mData)[2 * frame + channel]
        : static_cast<const float*>(list->mBuffers[channel].mData)[frame];
}
void set(AudioBufferList* list, std::size_t frame, unsigned channel, float value) {
    if (list->mNumberBuffers == 1) static_cast<float*>(list->mBuffers[0].mData)[2 * frame + channel] = value;
    else static_cast<float*>(list->mBuffers[channel].mData)[frame] = value;
}
OSStatus callback(AudioObjectID, const AudioTimeStamp*, const AudioBufferList* input,
                  const AudioTimeStamp* inputTime, AudioBufferList* output,
                  const AudioTimeStamp* outputTime, void* raw) {
    auto& c = *static_cast<Context*>(raw);
    // Every output buffer is initialized even for the recording process.
    if (output) for (UInt32 i = 0; i < output->mNumberBuffers; ++i)
        if (output->mBuffers[i].mData) std::memset(output->mBuffers[i].mData, 0, output->mBuffers[i].mDataByteSize);
    std::size_t frames = 0;
    if (!stereo(c.writer ? output : input, frames)) { c.badLayout.fetch_add(1, std::memory_order_relaxed); return noErr; }
    const auto* time = c.writer ? outputTime : inputTime;
    const bool valid = time && (time->mFlags & kAudioTimeStampSampleTimeValid) && std::isfinite(time->mSampleTime);
    if (!valid) c.noTime.fetch_add(1, std::memory_order_relaxed);
    if (c.writer && valid) {
        const auto origin = static_cast<std::int64_t>(std::llround(time->mSampleTime));
        for (std::size_t i = 0; i < frames; ++i) {
            auto tick = (origin + static_cast<std::int64_t>(i)) % period;
            if (tick < 0) tick += period;
            const float value = static_cast<float>(tick + 1) / scale;
            set(output, i, 0, value); set(output, i, 1, -value);
        }
    } else if (!c.writer) {
        const auto count = std::min(frames, c.captured.size() - c.used);
        for (std::size_t i = 0; i < count; ++i)
            c.captured[c.used + i] = { get(input, i, 0), get(input, i, 1),
                valid ? time->mSampleTime + static_cast<double>(i) : 0.0, valid };
        c.used += count;
        if (count != frames) c.truncated.fetch_add(1, std::memory_order_relaxed);
    }
    c.callbacks.fetch_add(1, std::memory_order_relaxed);
    return noErr;
}
AudioObjectPropertyAddress prop(AudioObjectPropertySelector s, AudioObjectPropertyScope scope = kAudioObjectPropertyScopeGlobal) {
    return { s, scope, kAudioObjectPropertyElementMain };
}
bool channels(AudioDeviceID device, AudioObjectPropertyScope scope) {
    auto p = prop(kAudioDevicePropertyStreamConfiguration, scope); UInt32 bytes = 0;
    if (AudioObjectGetPropertyDataSize(device, &p, 0, nullptr, &bytes) != noErr || bytes < sizeof(AudioBufferList)) return false;
    std::vector<std::uint64_t> data((bytes + 7) / 8);
    auto* list = reinterpret_cast<AudioBufferList*>(data.data());
    if (AudioObjectGetPropertyData(device, &p, 0, nullptr, &bytes, list) != noErr) return false;
    unsigned total = 0; for (UInt32 i = 0; i < list->mNumberBuffers; ++i) total += list->mBuffers[i].mNumberChannels;
    return total == 2;
}
}

int main(int argc, char** argv) {
    if (argc != 4 || (std::string(argv[1]) != "write" && std::string(argv[1]) != "read")) {
        std::cerr << "Usage: StudioForgeLinkHalNativeProbe write|read DEVICE_UID SECONDS (1..20)\n"; return 2;
    }
    int seconds = 0;
    try { seconds = std::stoi(argv[3]); } catch (...) { return 2; }
    if (seconds < 1 || seconds > 20) return 2;
    CFStringRef uid = CFStringCreateWithCString(nullptr, argv[2], kCFStringEncodingUTF8);
    if (!uid) return 2;
    auto p = prop(kAudioHardwarePropertyTranslateUIDToDevice); AudioDeviceID device = kAudioObjectUnknown;
    UInt32 size = sizeof(device);
    const auto status = AudioObjectGetPropertyData(kAudioObjectSystemObject, &p, sizeof(uid), &uid, &size, &device);
    CFRelease(uid);
    if (status != noErr || device == kAudioObjectUnknown) {
        std::cerr << "Device UID not found or Core Audio unavailable: " << status << "\n"; return 1;
    }
    const bool writer = std::string(argv[1]) == "write";
    const auto scope = writer ? kAudioObjectPropertyScopeOutput : kAudioObjectPropertyScopeInput;
    if (!channels(device, scope)) { std::cerr << "Expected exactly two channels in requested direction\n"; return 1; }
    AudioStreamBasicDescription format {}; size = sizeof(format); p = prop(kAudioDevicePropertyStreamFormat, scope);
    if (AudioObjectGetPropertyData(device, &p, 0, nullptr, &size, &format) != noErr ||
        format.mFormatID != kAudioFormatLinearPCM || !(format.mFormatFlags & kAudioFormatFlagIsFloat) ||
        format.mBitsPerChannel != 32 ||
        (format.mSampleRate != 44100.0 && format.mSampleRate != 48000.0)) {
        std::cerr << "Requested direction must expose 44.1/48 kHz Float32 PCM\n"; return 1;
    }
    Context context { writer, std::vector<Sample>(writer ? 0
        : static_cast<std::size_t>((seconds + 2) * format.mSampleRate)) };
    AudioDeviceIOProcID io = nullptr;
    auto result = AudioDeviceCreateIOProcID(device, callback, &context, &io);
    if (result != noErr) { std::cerr << "Create IO failed: " << result << "\n"; return 1; }
    result = AudioDeviceStart(device, io);
    if (result != noErr) { std::cerr << "Start failed (check microphone permission): " << result << "\n"; AudioDeviceDestroyIOProcID(device, io); return 1; }
    std::this_thread::sleep_for(std::chrono::seconds(seconds));
    const auto stopped = AudioDeviceStop(device, io);
    AudioDeviceDestroyIOProcID(device, io);
    std::cout << "callbacks=" << context.callbacks << " bad_layout=" << context.badLayout
              << " invalid_timestamps=" << context.noTime << " capture_truncations=" << context.truncated << "\n";
    if (!writer) {
        std::size_t nonzero = 0, matched = 0, discontinuities = 0, timed = 0, stereoIdentityFailures = 0;
        std::size_t firstSignalFrame = context.used, lastSignalFrame = 0;
        std::int64_t previous = -1, minDelay = period, maxDelay = -period;
        for (std::size_t i = 0; i < context.used; ++i) {
            const auto& s = context.captured[i];
            if (std::fabs(s.left) < 1e-7f && std::fabs(s.right) < 1e-7f) continue;
            ++nonzero;
            firstSignalFrame = std::min(firstSignalFrame, i); lastSignalFrame = i;
            const auto tick = static_cast<std::int64_t>(std::llround(s.left * scale)) - 1;
            if (std::fabs(s.left + s.right) > 1e-5f) ++stereoIdentityFailures;
            if (tick < 0 || tick >= period || std::fabs(s.left + s.right) > 1e-5f ||
                std::fabs(s.left * scale - static_cast<float>(tick + 1)) > 0.1f) continue;
            ++matched;
            if (previous >= 0 && tick != (previous + 1) % period) ++discontinuities;
            previous = tick;
            if (s.hasTime) {
                auto delay = (static_cast<std::int64_t>(std::llround(s.inputTime)) - tick) % period;
                if (delay > period/2) delay -= period; if (delay < -period/2) delay += period;
                minDelay = std::min(minDelay, delay); maxDelay = std::max(maxDelay, delay); ++timed;
            }
        }
        std::cout << "captured=" << context.used << " nonzero=" << nonzero << " pattern_matched=" << matched
                  << " stereo_identity_failures=" << stereoIdentityFailures
                  << " discontinuities=" << discontinuities;
        if (nonzero) std::cout << " first_signal_frame=" << firstSignalFrame << " last_signal_frame=" << lastSignalFrame;
        std::cout << "\n";
        if (timed) std::cout << "sample_time_offset_frames_min=" << minDelay << " max=" << maxDelay
                             << " (modulo " << period << "; valid only for a shared device timeline)\n";
        std::cout << "HAL FIFO occupancy/overruns are not exposed; silence and discontinuities are observations, not precise underrun counters.\n";
        if (!matched) { std::cerr << "No identifiable signal observed\n"; return 1; }
    }
    return stopped == noErr && context.callbacks && !context.badLayout && !context.truncated ? 0 : 1;
}
