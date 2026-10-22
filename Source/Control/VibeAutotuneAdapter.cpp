#include "VibeAutotuneAdapter.h"

namespace
{
juce::String normalized(juce::String value)
{
    return value.toLowerCase().retainCharacters("abcdefghijklmnopqrstuvwxyz0123456789");
}

juce::String findAlias(const std::vector<EffectParameterDescriptor>& parameters,
                       const juce::StringArray& aliases)
{
    for (const auto& alias : aliases)
        for (const auto& parameter : parameters)
            if ((normalized(parameter.identifier) == alias || normalized(parameter.name) == alias)
                && parameter.stableIdentifier && parameter.automatable && ! parameter.readOnly)
                return parameter.identifier.isNotEmpty() ? parameter.identifier : parameter.name;
    return {};
}

bool isAntaresAutoTuneName(const juce::String& source)
{
    const auto value = normalized(source);
    if (value.contains("autokey") || value.contains("vocaleq"))
        return false;
    static const char* products[] {
        "autotunepro", "autotuneprox", "autotuneartist", "autotunehybrid",
        "autotuneefx", "autotuneaccess", "autotuneadvanced"
    };
    for (const auto* product : products)
        if (value.contains(product))
            return true;
    // The current product is branded simply "AutoTune". Exact/suffixed
    // matches accept version decorations without admitting Auto-Key or the
    // other Antares products deliberately excluded above.
    return value == "autotune" || value.startsWith("autotune20");
}

bool isWavesTuneRealTimeName(const juce::String& source)
{
    const auto value = normalized(source);
    // Waves has shipped the same processor under both the long product name
    // and the abbreviated "WavesTune RT" display name. Deliberately exclude
    // the offline Waves Tune processor: only the real-time variant belongs in
    // the live detected-key bridge.
    return value.contains("wavestunerealtime") || value.contains("wavestunert");
}

bool sameScaleText(const juce::String& actual, const MusicalKey& requested)
{
    const auto value = normalized(actual);
    return requested.isMinor() ? value.contains("minor") || value == "min" || value == "aeolian"
                               : value.contains("major") || value == "maj" || value == "ionian";
}

bool sameRootText(const juce::String& actual, const MusicalKey& requested)
{
    // Reuse MusicalKey's enharmonic parsing instead of rejecting an Antares
    // readback such as Gb after StudioForge requested F#.
    const auto scale = requested.isMinor() ? "Minor" : "Major";
    const auto compact = actual.trim();
    const auto candidates = juce::StringArray::fromTokens(compact, "/| ", {});
    for (const auto& candidate : candidates)
        if (const auto parsed = MusicalKey::parse(candidate, scale);
            parsed.has_value() && parsed->rootNote() == requested.rootNote())
            return true;
    return false;
}
}

bool VibeAutotuneAdapter::supportsProduct(const juce::String& name,
                                          const juce::String& persistentIdentifier)
{
    const auto compactName = normalized(name);
    const auto compactIdentifier = normalized(persistentIdentifier);
    return compactName == "vibeautotune" || compactIdentifier.contains("vibeautotune")
        || isAntaresAutoTuneName(name) || isAntaresAutoTuneName(persistentIdentifier)
        || isWavesTuneRealTimeName(name) || isWavesTuneRealTimeName(persistentIdentifier);
}

VibeAutotuneAdapter::Result VibeAutotuneAdapter::resolve(const AudioEffectProcessor& effect,
                                                          const juce::String& configuredRoot,
                                                          const juce::String& configuredScale) const
{
    Result result;
    const auto parameters = effect.getParameterDescriptors();
    if (parameters.empty())
    {
        // Older/custom wrappers do not enumerate. A persisted, explicit route
        // remains a controlled compatibility fallback, never a parameter index.
        if (configuredRoot.isEmpty() || configuredScale.isEmpty())
        {
            result.error = "Pitch-correction plug-in does not expose parameter metadata";
            return result;
        }
        result = { true, { configuredRoot, configuredScale }, {} };
        return result;
    }

    const auto root = findAlias(parameters, { normalized(configuredRoot), "root", "key", "rootnote", "keyroot",
                                                   "keynote", "musicalkey", "targetkey", "keysignature",
                                                   "scaleroot" });
    const auto scale = findAlias(parameters, { normalized(configuredScale), "scale", "mode", "keyscale",
                                                    "scaletype", "musicalscale" });
    if (root.isEmpty() || scale.isEmpty())
    {
        result.error = root.isEmpty() ? "Pitch-correction root/key parameter is missing or not automatable"
                                      : "Pitch-correction scale/mode parameter is missing or not automatable";
        return result;
    }
    result = { true, { root, scale }, {} };
    return result;
}

VibeAutotuneAdapter::Result VibeAutotuneAdapter::apply(AudioEffectProcessor& effect, const MusicalKey& key,
                                                        const juce::String& configuredRoot,
                                                        const juce::String& configuredScale) const
{
    auto result = resolve(effect, configuredRoot, configuredScale);
    if (! result.succeeded) return result;
    if (! effect.setParameterText(result.mapping.root, key.rootName()))
    {
        result.succeeded = false;
        result.error = "Pitch-correction plug-in rejected the resolved root value";
        return result;
    }

    const auto appliedRoot = effect.getParameterText(result.mapping.root);
    if (appliedRoot.isNotEmpty() && ! sameRootText(appliedRoot, key))
    {
        result.succeeded = false;
        result.error = "Pitch-correction root readback does not match the requested key";
        return result;
    }

    // Vibe labels its diatonic minor mode "Natural Minor" while several
    // Antares generations expose the same musical mode as "Minor". Try the
    // canonical value first, then the equivalent vendor spelling, and accept
    // only a readback that is musically equivalent.
    juce::StringArray scaleValues { key.scaleName() };
    if (key.isMinor()) scaleValues.addIfNotAlreadyThere("Minor");
    auto scaleAccepted = false;
    for (const auto& value : scaleValues)
    {
        if (! effect.setParameterText(result.mapping.scale, value)) continue;
        const auto readback = effect.getParameterText(result.mapping.scale);
        if (readback.isEmpty() || sameScaleText(readback, key))
        {
            scaleAccepted = true;
            break;
        }
    }
    if (! scaleAccepted)
    {
        result.succeeded = false;
        result.error = "Pitch-correction scale readback does not match the requested scale";
    }
    return result;
}
