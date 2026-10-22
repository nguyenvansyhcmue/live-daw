#include <juce_audio_processors/juce_audio_processors.h>

#include <array>
#include <cmath>
#include <iostream>

int main(int argc, char* argv[])
{
    // Normal scanner mode keeps the established three-argument contract.
    // `--audit-parameters` is an explicit diagnostic mode used by release
    // validation; it never writes into a user project or plug-in preset.
    if (argc != 3 && argc != 4)
        return 64;

    const auto option = argc == 4 ? juce::String(argv[3]) : juce::String {};
    const auto auditParameters = option == "--audit-parameters";
    const auto requestedFormat = option.startsWith("--format=")
        ? option.fromFirstOccurrenceOf("=", false, false) : juce::String("VST3");
    if (argc == 4 && ! auditParameters && ! option.startsWith("--format="))
        return 64;

    const juce::String source { argv[1] };
    const juce::File output { argv[2] };
    if (requestedFormat.equalsIgnoreCase("VST3")
        && (! juce::File { source }.exists() || ! juce::File { source }.hasFileExtension(".vst3")))
        return 65;

    juce::AudioPluginFormatManager formats;
    formats.addDefaultFormats();
    for (auto* format : formats.getFormats())
    {
        if (format == nullptr || ! format->getName().equalsIgnoreCase(requestedFormat))
            continue;

        juce::OwnedArray<juce::PluginDescription> descriptions;
        format->findAllTypesForFile(descriptions, source);
        if (descriptions.isEmpty())
            return 66;

        // StudioForge insert slots currently host audio effects. Do not admit
        // an instrument merely because it shares a component bundle with one.
        for (auto index = descriptions.size(); --index >= 0;)
            if (descriptions[index] == nullptr || descriptions[index]->isInstrument)
                descriptions.remove(index);
        if (descriptions.isEmpty())
            return 71;

        // Metadata alone is insufficient: some bundles only fail while their
        // component is constructed. This helper is intentionally disposable.
        juce::String error;
        auto instance = formats.createPluginInstance(*descriptions[0], 48000.0, 512, error);
        if (instance == nullptr)
            return 69;

        // Metadata/instantiation alone does not exercise the VST3 audio-bus
        // mapper. Verify the exact stereo live-host contract before accepting
        // a bundle into StudioForge's registry.
        auto layout = instance->getBusesLayout();
        if (instance->getBusCount(true) > 0)
            layout.getMainInputChannelSet() = juce::AudioChannelSet::stereo();
        if (instance->getBusCount(false) > 0)
            layout.getMainOutputChannelSet() = juce::AudioChannelSet::stereo();
        if (! instance->setBusesLayout(layout))
            return 70;
        instance->enableAllBuses();
        instance->setPlayConfigDetails(2, 2, 48000.0, 512);
        instance->prepareToPlay(48000.0, 512);
        juce::AudioBuffer<float> testBuffer(2, 128);
        testBuffer.clear();
        juce::MidiBuffer midi;
        instance->processBlock(testBuffer, midi);
        instance->releaseResources();

        if (auditParameters)
        {
            juce::XmlElement report { "STUDIOFORGE_PLUGIN_PARAMETER_AUDIT" };
            report.setAttribute("plugin", descriptions[0]->name);
            report.setAttribute("format", descriptions[0]->pluginFormatName);
            report.setAttribute("parameterCount", instance->getParameters().size());

            int vendorIdentifierCount = 0;
            int mappableParameterCount = 0;
            int roundTripFailures = 0;
            int exerciseFailures = 0;
            for (int index = 0; index < instance->getParameters().size(); ++index)
            {
                auto* parameter = instance->getParameters()[index];
                if (parameter == nullptr) continue;

                auto* item = report.createNewChildElement("PARAMETER");
                item->setAttribute("index", index);
                item->setAttribute("name", parameter->getName(256));
                item->setAttribute("unit", parameter->getLabel());
                item->setAttribute("value", parameter->getCurrentValueAsText());
                item->setAttribute("automatable", parameter->isAutomatable());

                const auto* identified = dynamic_cast<const juce::AudioProcessorParameterWithID*>(parameter);
                const auto vendorIdentifier = identified != nullptr ? identified->getParameterID() : juce::String {};
                const auto hasVendorIdentifier = vendorIdentifier.isNotEmpty();
                const auto identifier = hasVendorIdentifier ? vendorIdentifier
                                                            : "studioforge-index:" + juce::String(index);
                const auto safelyMappable = parameter->isAutomatable() && identifier.isNotEmpty();
                item->setAttribute("id", identifier);
                item->setAttribute("vendorId", hasVendorIdentifier);
                item->setAttribute("mappable", safelyMappable);

                bool roundTrip = true;
                bool exercise = true;
                if (safelyMappable)
                {
                    ++mappableParameterCount;
                    if (hasVendorIdentifier) ++vendorIdentifierCount;
                    const auto before = parameter->getValue();
                    parameter->beginChangeGesture();
                    parameter->setValueNotifyingHost(before);
                    parameter->endChangeGesture();
                    roundTrip = std::abs(parameter->getValue() - before) <= 0.00001f;
                    if (! roundTrip) ++roundTripFailures;

                    // Exercise the same normalised range used by the THM
                    // surface. Discrete parameters may quantise these values,
                    // so correctness means the host accepts each write and
                    // restores the exact starting state before process exit.
                    for (const auto probeValue : std::array { 0.2f, 0.5f, 0.8f })
                    {
                        parameter->beginChangeGesture();
                        parameter->setValueNotifyingHost(probeValue);
                        parameter->endChangeGesture();
                        const auto observed = parameter->getValue();
                        item->setAttribute("textAt" + juce::String(juce::roundToInt(probeValue * 100.0f)),
                                           parameter->getCurrentValueAsText());
                        exercise = exercise && std::isfinite(observed) && observed >= 0.0f && observed <= 1.0f;
                    }
                    parameter->beginChangeGesture();
                    parameter->setValueNotifyingHost(before);
                    parameter->endChangeGesture();
                    exercise = exercise && std::abs(parameter->getValue() - before) <= 0.00001f;
                    if (! exercise) ++exerciseFailures;
                }
                item->setAttribute("roundTrip", roundTrip);
                item->setAttribute("exercise", exercise);
            }
            report.setAttribute("vendorIdentifierCount", vendorIdentifierCount);
            report.setAttribute("mappableParameterCount", mappableParameterCount);
            report.setAttribute("roundTripFailures", roundTripFailures);
            report.setAttribute("exerciseFailures", exerciseFailures);
            return output.replaceWithText(report.toString()) ? 0 : 67;
        }

        juce::XmlElement document { "KNOWNPLUGINS" };
        for (const auto* description : descriptions)
            if (description != nullptr)
                document.addChildElement(description->createXml().release());
        // writeTo() uses a second temporary file internally. This helper already
        // owns a private output path, so a direct atomic replacement avoids a
        // nested temporary-file failure in restricted/macOS launch contexts.
        return output.replaceWithText(document.toString()) ? 0 : 67;
    }

    return 68;
}
