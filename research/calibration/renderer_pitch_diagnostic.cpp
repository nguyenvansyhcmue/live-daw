#include <signalsmith-stretch/signalsmith-stretch.h>

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <numbers>
#include <vector>

namespace
{
constexpr double sampleRate = 48000.0;

double estimateAutocorrelationF0 (const std::vector<float>& values, int begin, int end,
                                  double expectedHz)
{
    const auto expectedLag = sampleRate / expectedHz;
    const auto minLag = std::max (2, static_cast<int> (std::floor (expectedLag * 0.93)));
    const auto maxLag = std::min (end - begin - 2, static_cast<int> (std::ceil (expectedLag * 1.07)));
    auto bestLag = minLag;
    auto bestCorrelation = -1.0;
    for (auto lag = minLag; lag <= maxLag; ++lag)
    {
        auto dot = 0.0, aa = 0.0, bb = 0.0;
        for (auto index = begin; index + lag < end; ++index)
        {
            const auto a = static_cast<double> (values[static_cast<size_t> (index)]);
            const auto b = static_cast<double> (values[static_cast<size_t> (index + lag)]);
            dot += a * b;
            aa += a * a;
            bb += b * b;
        }
        const auto correlation = dot / std::sqrt (aa * bb + 1.0e-30);
        if (correlation > bestCorrelation)
        {
            bestCorrelation = correlation;
            bestLag = lag;
        }
    }
    return sampleRate / static_cast<double> (bestLag);
}

void run (int fftSize, int interval, double sourceHz, double ratio, bool formantBase)
{
    signalsmith::stretch::SignalsmithStretch<float> stretch;
    stretch.configure (1, fftSize, interval, true);
    if (formantBase)
        stretch.setFormantBase (static_cast<float> (200.0 / sampleRate));
    stretch.setTransposeFactor (static_cast<float> (ratio));

    constexpr auto block = 64;
    const auto length = static_cast<int> (sampleRate * 6.0);
    std::vector<float> input (block), output (block), all;
    all.reserve (length);
    struct Input { const float* p; const float* operator[] (int) const { return p; } } source { input.data() };
    struct Output { float* p; float* operator[] (int) const { return p; } } destination { output.data() };
    for (auto start = 0; start < length; start += block)
    {
        for (auto n = 0; n < block; ++n)
        {
            const auto t = static_cast<double> (start + n) / sampleRate;
            input[static_cast<size_t> (n)] = static_cast<float> (0.30 * std::sin (2.0 * std::numbers::pi * sourceHz * t)
                + 0.10 * std::sin (4.0 * std::numbers::pi * sourceHz * t));
        }
        stretch.process (source, block, destination, block);
        all.insert (all.end(), output.begin(), output.end());
    }
    const auto expected = sourceHz * ratio;
    const auto begin = stretch.inputLatency() + stretch.outputLatency() + static_cast<int> (sampleRate);
    const auto actual = estimateAutocorrelationF0 (all, begin, static_cast<int> (all.size()), expected);
    const auto cents = 1200.0 * std::log2 (actual / expected);
    std::cout << "renderer_ac | fft=" << fftSize << " interval=" << interval
              << " source=" << sourceHz << " ratio=" << ratio
              << " formant_base=" << formantBase << " latency="
              << stretch.inputLatency() + stretch.outputLatency() << " actual=" << actual
              << " expected=" << expected << " cents=" << cents << '\n';
}
}

int main()
{
    std::cout << std::fixed << std::setprecision (3);
    for (const auto [fftSize, interval] : { std::pair { 512, 64 }, std::pair { 1024, 128 }, std::pair { 2048, 256 } })
        for (const auto formantBase : { false, true })
            for (const auto source : { 110.0, 220.0 })
            for (const auto ratio : { 0.90, 0.93, 0.95, 0.97, std::exp2 (-40.0 / 1200.0), 0.99,
                                       1.0, std::exp2 (40.0 / 1200.0), 1.03, 1.05, 1.10 })
                    run (fftSize, interval, source, ratio, formantBase);
}
