#pragma once

#include <cmath>

enum class TimelineWheelIntent
{
    panHorizontal,
    panVertical,
    zoomHorizontal,
    zoomTrackHeight,
    zoomWaveformAmplitude
};

struct TimelineWheelGesture final
{
    bool commandOrControl = false;
    bool alt = false;
    bool shift = false;
    float deltaX = 0.0f;
    float deltaY = 0.0f;
};

inline TimelineWheelIntent timelineWheelIntent(const TimelineWheelGesture& gesture) noexcept
{
    // Option/Alt is reserved for the waveform's vertical amplitude.  The
    // platform primary modifier is Command on macOS and Ctrl on Windows;
    // adding Shift changes the other geometric axis (track height).
    if (gesture.alt) return TimelineWheelIntent::zoomWaveformAmplitude;
    if (gesture.commandOrControl && gesture.shift) return TimelineWheelIntent::zoomTrackHeight;
    if (gesture.commandOrControl) return TimelineWheelIntent::zoomHorizontal;
    return gesture.shift || std::abs(gesture.deltaX) > std::abs(gesture.deltaY)
        ? TimelineWheelIntent::panHorizontal : TimelineWheelIntent::panVertical;
}
