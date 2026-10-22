#include "virtual-device/macos/VirtualInputFormat.h"

#include <cassert>

using studioforge::link::macos::VirtualInputFormat;

int main()
{
    assert(VirtualInputFormat {}.isSupported());
    assert((VirtualInputFormat { 44100.0, 2, 32, true, 1024 }.isSupported()));
    assert((! VirtualInputFormat { 96000.0, 2, 32, true, 256 }.isSupported()));
    assert((! VirtualInputFormat { 48000.0, 1, 32, true, 256 }.isSupported()));
    assert((! VirtualInputFormat { 48000.0, 2, 24, true, 256 }.isSupported()));
    assert((! VirtualInputFormat { 48000.0, 2, 32, false, 256 }.isSupported()));
    assert((! VirtualInputFormat { 48000.0, 2, 32, true, 32 }.isSupported()));
    assert((! VirtualInputFormat { 48000.0, 2, 32, true, 2048 }.isSupported()));
}
