#include "core/AudioFormat.h"

#include <limits>

int main()
{
    using studioforge::link::AudioFormat;
    if (AudioFormat {}.isValid()) return 1;
    if (! AudioFormat { 48000.0, 2 }.isValid()) return 2;
    if (! AudioFormat { 44100.0, 1 }.isValid()) return 3;
    if (AudioFormat { 48000.0, 0 }.isValid()) return 4;
    if (AudioFormat { -1.0, 2 }.isValid()) return 5;
    if (AudioFormat { std::numeric_limits<double>::infinity(), 2 }.isValid()) return 6;
    if (AudioFormat { std::numeric_limits<double>::quiet_NaN(), 2 }.isValid()) return 7;
    return 0;
}
