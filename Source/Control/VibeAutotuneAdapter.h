#pragma once

#include "MusicalKey.h"
#include "../AudioEngine/AudioEffectProcessor.h"

class VibeAutotuneAdapter final
{
public:
    struct Mapping { juce::String root; juce::String scale; };
    struct Result
    {
        bool succeeded = false;
        Mapping mapping;
        juce::String error;
    };

    Result resolve(const AudioEffectProcessor&, const juce::String& configuredRoot,
                   const juce::String& configuredScale) const;
    Result apply(AudioEffectProcessor&, const MusicalKey&, const juce::String& configuredRoot,
                 const juce::String& configuredScale) const;

    // Kept on the existing adapter type to preserve the serialized routing
    // contract. The implementation now covers StudioForge Vibe and the
    // supported Antares Auto-Tune family through public host parameters.
    static bool supportsProduct(const juce::String& name,
                                const juce::String& persistentIdentifier = {});
};
