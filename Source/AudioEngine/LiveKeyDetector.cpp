#include "LiveKeyDetector.h"

#include <algorithm>
#include <cmath>

namespace
{
constexpr std::array<float, 12> majorProfile { 6.35f, 2.23f, 3.48f, 2.33f, 4.38f, 4.09f,
                                                 2.52f, 5.19f, 2.39f, 3.66f, 2.29f, 2.88f };
constexpr std::array<float, 12> minorProfile { 6.33f, 2.68f, 3.52f, 5.38f, 2.60f, 3.53f,
                                                 2.54f, 4.75f, 3.98f, 2.69f, 3.34f, 3.17f };

float correlation(const std::array<float, 12>& values, const std::array<float, 12>& profile, int shift) noexcept
{
    float sumValues = 0.0f, sumProfile = 0.0f;
    for (int index = 0; index < 12; ++index)
    {
        sumValues += values[static_cast<size_t>(index)];
        sumProfile += profile[static_cast<size_t>((index - shift + 12) % 12)];
    }
    const auto meanValues = sumValues / 12.0f;
    const auto meanProfile = sumProfile / 12.0f;
    float numerator = 0.0f, valueEnergy = 0.0f, profileEnergy = 0.0f;
    for (int index = 0; index < 12; ++index)
    {
        const auto value = values[static_cast<size_t>(index)] - meanValues;
        const auto target = profile[static_cast<size_t>((index - shift + 12) % 12)] - meanProfile;
        numerator += value * target;
        valueEnergy += value * value;
        profileEnergy += target * target;
    }
    return numerator / std::sqrt(juce::jmax(1.0e-12f, valueEnergy * profileEnergy));
}
}

LiveKeyDetector::LiveKeyDetector() : juce::Thread("StudioForge Live Key Detector")
{
    startThread(juce::Thread::Priority::low);
}

LiveKeyDetector::~LiveKeyDetector()
{
    signalThreadShouldExit();
    stopThread(1500);
}

void LiveKeyDetector::push(const juce::AudioBuffer<float>& source, int numSamples, double sampleRate) noexcept
{
    if (numSamples <= 0 || source.getNumChannels() <= 0 || sampleRate <= 0.0)
        return;
    sourceSampleRate.store(sampleRate, std::memory_order_relaxed);

    int start1 = 0, size1 = 0, start2 = 0, size2 = 0;
    fifo.prepareToWrite(juce::jmin(numSamples, fifo.getFreeSpace()), start1, size1, start2, size2);
    const auto copy = [&source] (float* destination, int destinationStart, int sourceStart, int count) noexcept
    {
        const auto* left = source.getReadPointer(0, sourceStart);
        const auto* right = source.getNumChannels() > 1 ? source.getReadPointer(1, sourceStart) : left;
        for (int sample = 0; sample < count; ++sample)
            destination[destinationStart + sample] = 0.5f * (left[sample] + right[sample]);
    };
    copy(fifoSamples.data(), start1, 0, size1);
    copy(fifoSamples.data(), start2, size1, size2);
    fifo.finishedWrite(size1 + size2);
}

void LiveKeyDetector::pushDisplay(const juce::AudioBuffer<float>& source, int numSamples, double sampleRate) noexcept
{
    if (numSamples <= 0 || source.getNumChannels() <= 0 || sampleRate <= 0.0)
        return;
    displaySampleRate.store(sampleRate, std::memory_order_relaxed);
    int start1 = 0, size1 = 0, start2 = 0, size2 = 0;
    displayFifo.prepareToWrite(juce::jmin(numSamples, displayFifo.getFreeSpace()), start1, size1, start2, size2);
    const auto copy = [&source, this] (int destinationStart, int sourceStart, int count) noexcept
    {
        const auto* left = source.getReadPointer(0, sourceStart);
        const auto* right = source.getNumChannels() > 1 ? source.getReadPointer(1, sourceStart) : left;
        for (int sample = 0; sample < count; ++sample)
            displayFifoSamples[static_cast<size_t>(destinationStart + sample)] = 0.5f * (left[sample] + right[sample]);
    };
    copy(start1, 0, size1);
    copy(start2, size1, size2);
    displayFifo.finishedWrite(size1 + size2);
}

LiveKeyDetector::DisplaySnapshot LiveKeyDetector::getLatestDisplay() const
{
    const juce::ScopedLock lock(displayLock);
    return displaySnapshot;
}

void LiveKeyDetector::resetDisplay() noexcept
{
    displayResetGeneration.fetch_add(1, std::memory_order_acq_rel);
}

LiveKeyDetector::Result LiveKeyDetector::getLatestResult() const noexcept
{
    const auto packed = packedResult.load(std::memory_order_acquire);
    return { static_cast<int>(packed & 0x0fu), (packed & 0x10u) != 0,
             static_cast<float>((packed >> 5u) & 0xffu) / 255.0f, packed >> 13u };
}

void LiveKeyDetector::reset() noexcept
{
    packedResult.store(0, std::memory_order_release);
    resetGeneration.fetch_add(1, std::memory_order_acq_rel);
}

void LiveKeyDetector::run()
{
    std::vector<float> history;
    std::vector<float> displayHistory;
    double historyRate = 0.0;
    uint64_t revision = 0;
    int candidateRoot = -1;
    bool candidateMinor = false;
    int candidateHits = 0;
    int confirmedRoot = -1;
    bool confirmedMinor = false;
    auto observedResetGeneration = resetGeneration.load(std::memory_order_acquire);
    auto observedDisplayResetGeneration = displayResetGeneration.load(std::memory_order_acquire);
    auto lastAnalysis = juce::Time::getMillisecondCounterHiRes();
    auto lastDisplayAnalysis = lastAnalysis;
    while (! threadShouldExit())
    {
        const auto requestedReset = resetGeneration.load(std::memory_order_acquire);
        if (requestedReset != observedResetGeneration)
        {
            observedResetGeneration = requestedReset;
            history.clear();
            candidateRoot = -1;
            candidateMinor = false;
            candidateHits = 0;
            confirmedRoot = -1;
            confirmedMinor = false;
            int discardStart1 = 0, discardSize1 = 0, discardStart2 = 0, discardSize2 = 0;
            fifo.prepareToRead(fifo.getNumReady(), discardStart1, discardSize1,
                               discardStart2, discardSize2);
            fifo.finishedRead(discardSize1 + discardSize2);
            lastAnalysis = juce::Time::getMillisecondCounterHiRes();
        }
        const auto rate = sourceSampleRate.load(std::memory_order_relaxed);
        if (rate != historyRate)
        {
            history.clear();
            historyRate = rate;
            candidateRoot = -1;
            candidateMinor = false;
            candidateHits = 0;
            confirmedRoot = -1;
            confirmedMinor = false;
            packedResult.store(0, std::memory_order_release);
        }

        const auto requestedDisplayReset = displayResetGeneration.load(std::memory_order_acquire);
        if (requestedDisplayReset != observedDisplayResetGeneration)
        {
            observedDisplayResetGeneration = requestedDisplayReset;
            displayHistory.clear();
            int discardStart1 = 0, discardSize1 = 0, discardStart2 = 0, discardSize2 = 0;
            displayFifo.prepareToRead(displayFifo.getNumReady(), discardStart1, discardSize1,
                                      discardStart2, discardSize2);
            displayFifo.finishedRead(discardSize1 + discardSize2);
            {
                const juce::ScopedLock lock(displayLock);
                displaySnapshot = {};
            }
            lastDisplayAnalysis = juce::Time::getMillisecondCounterHiRes();
        }
        int start1 = 0, size1 = 0, start2 = 0, size2 = 0;
        fifo.prepareToRead(fifo.getNumReady(), start1, size1, start2, size2);
        history.insert(history.end(), fifoSamples.begin() + start1, fifoSamples.begin() + start1 + size1);
        history.insert(history.end(), fifoSamples.begin() + start2, fifoSamples.begin() + start2 + size2);
        fifo.finishedRead(size1 + size2);

        int displayStart1 = 0, displaySize1 = 0, displayStart2 = 0, displaySize2 = 0;
        displayFifo.prepareToRead(displayFifo.getNumReady(), displayStart1, displaySize1,
                                  displayStart2, displaySize2);
        displayHistory.insert(displayHistory.end(), displayFifoSamples.begin() + displayStart1,
                              displayFifoSamples.begin() + displayStart1 + displaySize1);
        displayHistory.insert(displayHistory.end(), displayFifoSamples.begin() + displayStart2,
                              displayFifoSamples.begin() + displayStart2 + displaySize2);
        displayFifo.finishedRead(displaySize1 + displaySize2);
        constexpr size_t displayWindow = 4096;
        if (displayHistory.size() > displayWindow)
            displayHistory.erase(displayHistory.begin(), displayHistory.end()
                                 - static_cast<std::vector<float>::difference_type>(displayWindow));

        const auto wantedSamples = static_cast<size_t>(juce::jmax(1.0, historyRate * 3.0));
        if (history.size() > wantedSamples)
            history.erase(history.begin(), history.begin()
                          + static_cast<std::vector<float>::difference_type>(history.size() - wantedSamples));

        const auto now = juce::Time::getMillisecondCounterHiRes();
        // Publish at ~30 Hz. The companion renders at display refresh rate and
        // interpolates between these bounded analysis frames, so the audio
        // worker stays comfortably below audio-thread priority.
        if (! displayHistory.empty() && now - lastDisplayAnalysis >= 33.0)
        {
            lastDisplayAnalysis = now;
            DisplaySnapshot next;
            double energy = 0.0;
            for (const auto sample : displayHistory) energy += static_cast<double>(sample) * sample;
            next.rms = static_cast<float>(std::sqrt(energy / displayHistory.size()));
            for (size_t point = 0; point < next.waveform.size(); ++point)
            {
                const auto begin = point * displayHistory.size() / next.waveform.size();
                const auto end = (point + 1) * displayHistory.size() / next.waveform.size();
                float peak = 0.0f;
                for (auto index = begin; index < end; ++index)
                    peak = juce::jmax(peak, std::abs(displayHistory[index]));
                next.waveform[point] = peak;
            }
            const auto rate = displaySampleRate.load(std::memory_order_relaxed);
            if (rate > 0.0)
            {
                std::array<double, displayWindow> windowed {};
                for (size_t sample = 0; sample < displayHistory.size(); ++sample)
                {
                    const auto window = 0.5 - 0.5 * std::cos(juce::MathConstants<double>::twoPi
                                                           * sample / juce::jmax<size_t>(1, displayHistory.size() - 1));
                    windowed[sample] = displayHistory[sample] * window;
                }
                for (size_t point = 0; point < next.spectrum.size(); ++point)
                {
                    const auto ratio = static_cast<double>(point) / (next.spectrum.size() - 1);
                    const auto frequency = 20.0 * std::pow(1000.0, ratio);
                    const auto step = juce::MathConstants<double>::twoPi * frequency / rate;
                    const auto rotateReal = std::cos(step);
                    const auto rotateImaginary = std::sin(step);
                    auto oscillatorReal = 1.0;
                    auto oscillatorImaginary = 0.0;
                    double real = 0.0, imaginary = 0.0;
                    for (size_t sample = 0; sample < displayHistory.size(); ++sample)
                    {
                        real += windowed[sample] * oscillatorReal;
                        imaginary -= windowed[sample] * oscillatorImaginary;
                        const auto nextReal = oscillatorReal * rotateReal - oscillatorImaginary * rotateImaginary;
                        oscillatorImaginary = oscillatorReal * rotateImaginary + oscillatorImaginary * rotateReal;
                        oscillatorReal = nextReal;
                    }
                    const auto magnitude = 2.0 * std::sqrt(real * real + imaginary * imaginary)
                                           / juce::jmax<size_t>(1, displayHistory.size());
                    const auto db = 20.0 * std::log10(juce::jmax(1.0e-8, magnitude));
                    next.spectrum[point] = static_cast<float>(juce::jlimit(0.0, 1.0, (db + 80.0) / 80.0));
                }
            }
            {
                const juce::ScopedLock lock(displayLock);
                next.revision = displaySnapshot.revision + 1;
                displaySnapshot = next;
            }
        }
        if (history.size() >= wantedSamples && now - lastAnalysis >= 1000.0)
        {
            lastAnalysis = now;
            const auto result = analyse(history, historyRate, revision);
            if (result.confidence < 0.60f)
            {
                candidateRoot = -1;
                candidateHits = 0;
                continue;
            }

            if (result.root == candidateRoot && result.minor == candidateMinor)
                ++candidateHits;
            else
            {
                candidateRoot = result.root;
                candidateMinor = result.minor;
                candidateHits = 1;
            }

            // Tune-AI waited for three matching observations. Keep that useful
            // safeguard, but publish only a confirmed *change* so plug-in
            // parameters are not rewritten every second.
            if (candidateHits < 3 || (candidateRoot == confirmedRoot && candidateMinor == confirmedMinor))
                continue;

            confirmedRoot = candidateRoot;
            confirmedMinor = candidateMinor;
            ++revision;
            const auto confidence = static_cast<uint64_t>(juce::jlimit(0, 255, juce::roundToInt(result.confidence * 255.0f)));
            packedResult.store((revision << 13u) | (confidence << 5u)
                                   | (confirmedMinor ? 0x10u : 0u) | static_cast<uint64_t>(confirmedRoot),
                               std::memory_order_release);
        }
        wait(8);
    }
}

LiveKeyDetector::Result LiveKeyDetector::analyse(const std::vector<float>& audio, double sampleRate, uint64_t revision) noexcept
{
    std::array<float, 12> chroma {};
    constexpr int frameSize = 4096;
    constexpr int hopSize = 2048;
    if (audio.size() < frameSize || sampleRate <= 0.0)
        return { 0, false, 0.0f, revision };

    for (size_t frame = 0; frame + frameSize <= audio.size(); frame += hopSize)
        for (int midi = 36; midi <= 84; ++midi)
        {
            const auto frequency = 440.0 * std::pow(2.0, (midi - 69) / 12.0);
            const auto step = juce::MathConstants<double>::twoPi * frequency / sampleRate;
            double real = 0.0, imaginary = 0.0;
            for (int sample = 0; sample < frameSize; ++sample)
            {
                const auto window = 0.5 - 0.5 * std::cos(juce::MathConstants<double>::twoPi * sample / (frameSize - 1));
                const auto value = static_cast<double>(audio[frame + static_cast<size_t>(sample)]) * window;
                const auto phase = step * sample;
                real += value * std::cos(phase);
                imaginary -= value * std::sin(phase);
            }
            chroma[static_cast<size_t>(midi % 12)] += static_cast<float>(real * real + imaginary * imaginary);
        }

    auto bestScore = -2.0f;
    auto secondScore = -2.0f;
    auto bestRoot = 0;
    auto bestMinor = false;
    const auto consider = [&] (float score, int root, bool isMinor)
    {
            if (score > bestScore)
            {
                secondScore = bestScore;
                bestScore = score;
                bestRoot = root;
                bestMinor = isMinor;
            }
            else if (score > secondScore) secondScore = score;
    };
    for (int root = 0; root < 12; ++root)
    {
        consider(correlation(chroma, majorProfile, root), root, false);
        consider(correlation(chroma, minorProfile, root), root, true);
    }
    const auto confidence = juce::jlimit(0.0f, 1.0f, (bestScore + 1.0f) * 0.5f
                                                     * juce::jlimit(0.0f, 1.0f, (bestScore - secondScore) * 3.0f));
    return { bestRoot, bestMinor, confidence, revision };
}
