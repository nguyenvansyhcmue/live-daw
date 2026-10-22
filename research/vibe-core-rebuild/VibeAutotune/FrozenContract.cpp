#include "PluginProcessor.h"
#include "PluginEditor.h"
namespace {
constexpr std::array<std::array<bool, 12>, 14> scaleIntervals {{
    {{ true, true, true, true, true, true, true, true, true, true, true, true }},   // Chromatic
    {{ true, false, true, false, true, true, false, true, false, true, false, true }}, // Major
    {{ true, false, true, true, false, true, false, true, true, false, true, false }}, // Natural minor
    {{ true, false, true, false, true, false, false, true, false, true, false, false }}, // Major pentatonic
    {{ true, false, false, true, false, true, false, true, false, false, true, false }}, // Minor pentatonic
    {{ true, false, true, true, false, true, false, true, true, false, false, true }}, // Harmonic minor
    {{ true, false, true, true, false, true, false, true, false, true, false, true }}, // Melodic minor (ascending)
    {{ true, false, true, false, true, true, false, true, false, true, true, false }}, // Dorian
    {{ true, true, false, true, false, true, false, true, true, false, true, false }}, // Phrygian
    {{ true, false, true, false, true, false, true, true, false, true, false, true }}, // Lydian
    {{ true, false, true, false, true, true, false, true, false, true, true, false }}, // Mixolydian
    {{ true, true, false, true, false, true, true, false, true, false, true, false }}, // Locrian
    {{ true, false, false, true, false, true, true, true, false, false, true, false }}, // Minor blues
    {{ true, false, true, false, true, false, true, false, true, false, true, false }}  // Whole tone
}};
constexpr int userScaleIndex = static_cast<int> (scaleIntervals.size());

constexpr uint8_t noteRuleValue (NoteRule rule) noexcept { return static_cast<uint8_t> (rule); }
constexpr NoteRule noteRuleFromValue (uint8_t value) noexcept
{
    return static_cast<NoteRule> (juce::jlimit (0, 4, static_cast<int> (value)));
}
}


juce::AudioProcessorValueTreeState::ParameterLayout VibeAutotuneProcessor::createParameterLayout()
{
    using Parameter = juce::AudioParameterFloat;
    using Choice = juce::AudioParameterChoice;
    using Bool = juce::AudioParameterBool;
    using Range = juce::NormalisableRange<float>;
    using FloatAttributes = juce::AudioParameterFloatAttributes;

    juce::AudioProcessorValueTreeState::ParameterLayout layout;
    layout.add (std::make_unique<Bool> (juce::ParameterID { "bypass", 1 }, "Bypass", false));
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "retuneSpeed", 1 }, "Retune Speed", Range (0.0f, 400.0f, 0.1f), 100.0f, FloatAttributes().withLabel ("ms")));
    // A new instance must land exactly on the selected scale note. Flex-Tune
    // is an explicit near-target relaxation, and its old non-zero default
    // made slower Retune settings sound as though they never reached target.
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "flexTune", 1 }, "Flex-Tune", Range (0.0f, 100.0f, 0.1f), 0.0f));
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "humanize", 1 }, "Humanize", Range (0.0f, 100.0f, 0.1f), 0.0f, FloatAttributes().withLabel ("%")));
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "naturalVibrato", 1 }, "Natural Vibrato", Range (-12.0f, 12.0f, 0.1f), 0.0f, FloatAttributes().withLabel (" ms")));
    // Hidden calibration-only controls. -1 restores the immutable production
    // knots; StudioForge uses these rather than environment propagation
    // through the AU host process.
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "diagnosticRetune10T90Ms", 1 }, "Diagnostic Retune 10 T90", Range (-1.0f, 80.0f, 0.1f), -1.0f));
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "diagnosticRetune25T90Ms", 1 }, "Diagnostic Retune 25 T90", Range (-1.0f, 140.0f, 0.1f), -1.0f));
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "diagnosticFlexResidualScale", 1 }, "Diagnostic Flex Residual", Range (0.5f, 1.5f, 0.01f), 1.0f));
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "diagnosticHumanizeScale", 1 }, "Diagnostic Humanize Scale", Range (0.5f, 1.5f, 0.01f), 1.0f));
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "diagnosticNegativeNaturalPhaseScale", 1 }, "Diagnostic Natural Phase", Range (0.0f, 2.5f, 0.01f), 1.0f));
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "diagnosticNaturalSurfaceHardTuneWeight", 1 }, "Diagnostic Natural Hard Tune Surface", Range (0.0f, 1.0f, 0.01f), 0.0f));
    layout.add (std::make_unique<Choice> (juce::ParameterID { "key", 1 }, "Key", juce::StringArray { "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B" }, 6));
    layout.add (std::make_unique<Choice> (juce::ParameterID { "scale", 1 }, "Scale", juce::StringArray {
        "Chromatic", "Major", "Natural Minor", "Major Pentatonic", "Minor Pentatonic",
        "Harmonic Minor", "Melodic Minor", "Dorian", "Phrygian", "Lydian",
        "Mixolydian", "Locrian", "Minor Blues", "Whole Tone", "User Scale" }, 2));
    layout.add (std::make_unique<Choice> (juce::ParameterID { "inputType", 1 }, "Input Type", juce::StringArray { "Soprano", "Alto", "Tenor", "Low" }, 1));
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "transpose", 1 }, "Transpose", Range (-12.0f, 12.0f, 1.0f), 0.0f, FloatAttributes().withLabel ("st")));
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "referencePitch", 1 }, "Reference Pitch", Range (432.0f, 448.0f, 0.1f), 440.0f, FloatAttributes().withLabel ("Hz")));
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "tracking", 1 }, "Tracking", Range (0.0f, 100.0f, 1.0f), 50.0f, FloatAttributes().withLabel ("%")));
    layout.add (std::make_unique<Parameter> (juce::ParameterID { "voicedColour", 1 }, "Voiced Colour", Range (0.0f, 100.0f, 0.1f), 0.0f, FloatAttributes().withLabel ("%")));
    return layout;
}

bool VibeAutotuneProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    const auto& input = layouts.getMainInputChannelSet();
    const auto& output = layouts.getMainOutputChannelSet();
    return input == output
        && (input == juce::AudioChannelSet::mono()
            || input == juce::AudioChannelSet::stereo());
}

bool VibeAutotuneProcessor::scaleContainsPitchClass (int root, int scale, int pitchClass) noexcept
{
    const auto safeRoot = juce::jlimit (0, 11, root);
    const auto safeScale = juce::jlimit (0, static_cast<int> (scaleIntervals.size()) - 1, scale);
    const auto safePitchClass = (pitchClass % 12 + 12) % 12;
    return scaleIntervals[static_cast<size_t> (safeScale)]
                         [static_cast<size_t> ((safePitchClass - safeRoot + 12) % 12)];
}

void VibeAutotuneProcessor::resetNotePolicyToScale (int key, int scale) noexcept
{
    const auto safeScale = juce::jlimit (0, userScaleIndex, scale);
    if (safeScale == userScaleIndex)
    {
        for (int pitchClass = 0; pitchClass < 12; ++pitchClass)
            pitchClassDefaultPolicy[static_cast<size_t> (pitchClass)].store (
                noteRuleValue (NoteRule::IllegalNearest), std::memory_order_relaxed);
        for (auto& hasOverride : midiNoteHasOverride)
            hasOverride.store (false, std::memory_order_relaxed);
        enabledNoteMask.store (0, std::memory_order_relaxed);
        baseScaleMask.store (0, std::memory_order_relaxed);
        synchronisedPolicyKey = juce::jlimit (0, 11, key);
        synchronisedPolicyScale = userScaleIndex;
        notePolicyRevision.fetch_add (1, std::memory_order_relaxed);
        return;
    }

    uint16_t mask = 0;
    for (int pitchClass = 0; pitchClass < 12; ++pitchClass)
    {
        const auto rule = scaleContainsPitchClass (key, safeScale, pitchClass)
                        ? NoteRule::Legal : NoteRule::IllegalNearest;
        pitchClassDefaultPolicy[static_cast<size_t> (pitchClass)].store (noteRuleValue (rule), std::memory_order_relaxed);
        if (isLegalNoteRule (rule))
            mask |= static_cast<uint16_t> (1u << pitchClass);
    }
    for (auto& hasOverride : midiNoteHasOverride)
        hasOverride.store (false, std::memory_order_relaxed);

    enabledNoteMask.store (mask, std::memory_order_relaxed);
    baseScaleMask.store (mask, std::memory_order_relaxed);
    notePolicyRevision.fetch_add (1, std::memory_order_relaxed);
    synchronisedPolicyKey = juce::jlimit (0, 11, key);
    synchronisedPolicyScale = safeScale;
}

void VibeAutotuneProcessor::synchroniseNotePolicyToScale() noexcept
{
    const auto key = juce::jlimit (0, 11, static_cast<int> (parameters.getRawParameterValue ("key")->load (std::memory_order_relaxed)));
    const auto scale = juce::jlimit (0, userScaleIndex,
                                     static_cast<int> (parameters.getRawParameterValue ("scale")->load (std::memory_order_relaxed)));
    if (key == synchronisedPolicyKey && scale == synchronisedPolicyScale)
        return;

    resetNotePolicyToScale (key, scale);
}

NotePolicySnapshot VibeAutotuneProcessor::makeNotePolicySnapshot() const noexcept
{
    NotePolicySnapshot snapshot;
    snapshot.groupOctaves = groupOctaves.load (std::memory_order_relaxed);
    // Voice is both an analyser profile and a musical target range. The
    // immutable snapshot keeps this UI-to-audio handoff realtime-safe.
    snapshot.targetRange = vocalTargetRangeForInputType (static_cast<int> (
        parameters.getRawParameterValue ("inputType")->load (std::memory_order_relaxed)));
    snapshot.midiTargetNote = midiTargetNote.load (std::memory_order_relaxed);
    for (int pitchClass = 0; pitchClass < 12; ++pitchClass)
        snapshot.pitchClassDefaults[static_cast<size_t> (pitchClass)] = noteRuleFromValue (
            pitchClassDefaultPolicy[static_cast<size_t> (pitchClass)].load (std::memory_order_relaxed));
    for (int midiNote = 0; midiNote <= 127; ++midiNote)
    {
        snapshot.midiNoteOverrides[static_cast<size_t> (midiNote)] = noteRuleFromValue (
            midiNoteOverridePolicy[static_cast<size_t> (midiNote)].load (std::memory_order_relaxed));
        snapshot.hasMidiNoteOverride[static_cast<size_t> (midiNote)] =
            midiNoteHasOverride[static_cast<size_t> (midiNote)].load (std::memory_order_relaxed);
    }
    return snapshot;
}

juce::String VibeAutotuneProcessor::getLatestDetectedNoteName() const
{
    return getPitchMonitorData().detectedNote;
}

int VibeAutotuneProcessor::getLatestDetectedMidiNote() const noexcept
{
    return latestDetectedMidiNote.load (std::memory_order_relaxed);
}

int VibeAutotuneProcessor::getLatestTargetMidiNote() const noexcept
{
    return latestTargetMidiNote.load (std::memory_order_relaxed);
}

uint16_t VibeAutotuneProcessor::getEnabledNoteMask() const noexcept
{
    return enabledNoteMask.load (std::memory_order_relaxed);
}

void VibeAutotuneProcessor::setEnabledNoteMask (uint16_t newMask) noexcept
{
    const auto mask = newMask == 0 ? static_cast<uint16_t> (1u) : static_cast<uint16_t> (newMask & 0x0fffu);
    for (int pitchClass = 0; pitchClass < 12; ++pitchClass)
        setNoteRuleForPitchClass (pitchClass, (mask & static_cast<uint16_t> (1u << pitchClass)) != 0
                                                  ? NoteRule::Legal : NoteRule::IllegalNearest);
    baseScaleMask.store (mask, std::memory_order_relaxed);
}

uint16_t VibeAutotuneProcessor::getBaseScaleMask() const noexcept
{
    return baseScaleMask.load (std::memory_order_relaxed);
}

bool VibeAutotuneProcessor::hasCustomNotePolicy() const noexcept
{
    const auto currentScale = static_cast<int> (*parameters.getRawParameterValue ("scale"));
    if (currentScale == userScaleIndex)
        return true;

    const auto baseMask = getBaseScaleMask();
    for (int pitchClass = 0; pitchClass < 12; ++pitchClass)
    {
        const auto defaultRule = (baseMask & static_cast<uint16_t> (1u << pitchClass)) != 0
                                   ? NoteRule::Legal : NoteRule::IllegalNearest;
        if (getNoteRuleForPitchClass (pitchClass) != defaultRule)
            return true;
    }

    if (! getGroupOctaves())
        for (int midiNote = 0; midiNote < 128; ++midiNote)
            if (getNoteRuleForMidiNote (midiNote) != getNoteRuleForPitchClass (midiNote % 12))
                return true;

    return false;
}

NoteRule VibeAutotuneProcessor::getNoteRuleForPitchClass (int pitchClass) const noexcept
{
    const auto safePitchClass = (pitchClass % 12 + 12) % 12;
    return noteRuleFromValue (pitchClassDefaultPolicy[static_cast<size_t> (safePitchClass)].load (std::memory_order_relaxed));
}

NoteRule VibeAutotuneProcessor::getNoteRuleForMidiNote (int midiNote) const noexcept
{
    if (midiNote < 0 || midiNote > 127)
        return NoteRule::IllegalNearest;
    const auto index = static_cast<size_t> (midiNote);
    if (midiNoteHasOverride[index].load (std::memory_order_relaxed))
        return noteRuleFromValue (midiNoteOverridePolicy[index].load (std::memory_order_relaxed));
    return getNoteRuleForPitchClass (midiNote % 12);
}

void VibeAutotuneProcessor::setNoteRuleForPitchClass (int pitchClass, NoteRule rule) noexcept
{
    const auto safePitchClass = (pitchClass % 12 + 12) % 12;
    pitchClassDefaultPolicy[static_cast<size_t> (safePitchClass)].store (noteRuleValue (rule), std::memory_order_relaxed);
    // A grouped edit changes every octave, so it also clears any local
    // exceptions for this pitch class.
    for (int midiNote = safePitchClass; midiNote <= 127; midiNote += 12)
        midiNoteHasOverride[static_cast<size_t> (midiNote)].store (false, std::memory_order_relaxed);

    auto mask = static_cast<uint16_t> (0);
    for (int note = 0; note < 12; ++note)
        if (isLegalNoteRule (getNoteRuleForPitchClass (note)))
            mask |= static_cast<uint16_t> (1u << note);
    enabledNoteMask.store (mask == 0 ? static_cast<uint16_t> (1u) : mask, std::memory_order_relaxed);
    notePolicyRevision.fetch_add (1, std::memory_order_relaxed);
}

void VibeAutotuneProcessor::setNoteRuleForMidiNote (int midiNote, NoteRule rule) noexcept
{
    if (midiNote < 0 || midiNote > 127)
        return;
    if (groupOctaves.load (std::memory_order_relaxed))
    {
        setNoteRuleForPitchClass (midiNote % 12, rule);
        return;
    }
    midiNoteOverridePolicy[static_cast<size_t> (midiNote)].store (noteRuleValue (rule), std::memory_order_relaxed);
    midiNoteHasOverride[static_cast<size_t> (midiNote)].store (true, std::memory_order_relaxed);
    notePolicyRevision.fetch_add (1, std::memory_order_relaxed);
}

void VibeAutotuneProcessor::resetNoteRuleForPitchClass (int pitchClass) noexcept
{
    const auto safePitchClass = (pitchClass % 12 + 12) % 12;
    const auto defaultRule = (getBaseScaleMask() & static_cast<uint16_t> (1u << safePitchClass)) != 0
                           ? NoteRule::Legal : NoteRule::IllegalNearest;
    setNoteRuleForPitchClass (safePitchClass, defaultRule);
}

void VibeAutotuneProcessor::resetNoteRuleForMidiNote (int midiNote) noexcept
{
    if (midiNote < 0 || midiNote > 127)
        return;

    if (groupOctaves.load (std::memory_order_relaxed))
    {
        resetNoteRuleForPitchClass (midiNote % 12);
        return;
    }

    midiNoteHasOverride[static_cast<size_t> (midiNote)].store (false, std::memory_order_relaxed);
    notePolicyRevision.fetch_add (1, std::memory_order_relaxed);
}

void VibeAutotuneProcessor::resetNotePolicyToCurrentScale() noexcept
{
    const auto key = juce::jlimit (0, 11,
        static_cast<int> (parameters.getRawParameterValue ("key")->load (std::memory_order_relaxed)));
    const auto scale = juce::jlimit (0, userScaleIndex,
        static_cast<int> (parameters.getRawParameterValue ("scale")->load (std::memory_order_relaxed)));
    resetNotePolicyToScale (key, scale);
}

bool VibeAutotuneProcessor::getGroupOctaves() const noexcept
{
    return groupOctaves.load (std::memory_order_relaxed);
}

void VibeAutotuneProcessor::setGroupOctaves (bool shouldGroup) noexcept
{
    groupOctaves.store (shouldGroup, std::memory_order_relaxed);
    notePolicyRevision.fetch_add (1, std::memory_order_relaxed);
}

juce::AudioProcessorParameter* VibeAutotuneProcessor::getBypassParameter() const
{
    return parameters.getParameter ("bypass");
}

void VibeAutotuneProcessor::getStateInformation (juce::MemoryBlock& destData)
{
    auto state = parameters.copyState();
    state.setProperty ("enabledNoteMask", static_cast<int> (getEnabledNoteMask()), nullptr);
    state.setProperty ("baseScaleMask", static_cast<int> (getBaseScaleMask()), nullptr);
    state.setProperty ("groupOctaves", getGroupOctaves(), nullptr);
    juce::String defaults, overrides, overrideMask;
    for (int pitchClass = 0; pitchClass < 12; ++pitchClass)
        defaults += juce::String (static_cast<int> (getNoteRuleForPitchClass (pitchClass)));
    for (int midiNote = 0; midiNote <= 127; ++midiNote)
    {
        const auto index = static_cast<size_t> (midiNote);
        overrides += juce::String (static_cast<int> (noteRuleFromValue (
            midiNoteOverridePolicy[index].load (std::memory_order_relaxed))));
        overrideMask += midiNoteHasOverride[index].load (std::memory_order_relaxed) ? "1" : "0";
    }
    state.setProperty ("noteMapVersion", 2, nullptr);
    state.setProperty ("pitchClassDefaultPolicy", defaults, nullptr);
    state.setProperty ("midiNoteOverridePolicy", overrides, nullptr);
    state.setProperty ("midiNoteOverrideMask", overrideMask, nullptr);
    juce::MemoryOutputStream stream (destData, true);
    state.writeToStream (stream);
}

void VibeAutotuneProcessor::setStateInformation (const void* data, int sizeInBytes)
{
    if (const auto state = juce::ValueTree::readFromData (data, static_cast<size_t> (sizeInBytes)); state.isValid())
    {
        parameters.replaceState (state);
        if (state.hasProperty ("pitchClassDefaultPolicy"))
        {
            const auto defaults = state.getProperty ("pitchClassDefaultPolicy").toString();
            const auto overrides = state.getProperty ("midiNoteOverridePolicy").toString();
            const auto overrideMask = state.getProperty ("midiNoteOverrideMask").toString();
            setGroupOctaves (static_cast<bool> (state.getProperty ("groupOctaves", true)));
            for (int pitchClass = 0; pitchClass < 12 && pitchClass < defaults.length(); ++pitchClass)
                pitchClassDefaultPolicy[static_cast<size_t> (pitchClass)].store (
                    noteRuleValue (noteRuleFromValue (static_cast<uint8_t> (defaults[pitchClass] - '0'))), std::memory_order_relaxed);
            for (int midiNote = 0; midiNote <= 127; ++midiNote)
            {
                const auto index = static_cast<size_t> (midiNote);
                const auto hasOverride = midiNote < overrideMask.length() && overrideMask[midiNote] == '1';
                midiNoteHasOverride[index].store (hasOverride, std::memory_order_relaxed);
                if (midiNote < overrides.length())
                    midiNoteOverridePolicy[index].store (
                        noteRuleValue (noteRuleFromValue (static_cast<uint8_t> (overrides[midiNote] - '0'))), std::memory_order_relaxed);
            }
        }
        else if (state.hasProperty ("groupedNotePolicy"))
        {
            // Safe migration from the original flattened map.  Any MIDI rule
            // different from its pitch-class default becomes an override.
            const auto grouped = state.getProperty ("groupedNotePolicy").toString();
            const auto perMidi = state.getProperty ("perMidiNotePolicy").toString();
            setGroupOctaves (static_cast<bool> (state.getProperty ("groupOctaves", true)));
            for (int pitchClass = 0; pitchClass < 12 && pitchClass < grouped.length(); ++pitchClass)
                pitchClassDefaultPolicy[static_cast<size_t> (pitchClass)].store (
                    noteRuleValue (noteRuleFromValue (static_cast<uint8_t> (grouped[pitchClass] - '0'))), std::memory_order_relaxed);
            for (int midiNote = 0; midiNote <= 127; ++midiNote)
            {
                const auto index = static_cast<size_t> (midiNote);
                const auto defaultRule = getNoteRuleForPitchClass (midiNote % 12);
                const auto restoredRule = midiNote < perMidi.length()
                                        ? noteRuleFromValue (static_cast<uint8_t> (perMidi[midiNote] - '0')) : defaultRule;
                midiNoteOverridePolicy[index].store (noteRuleValue (restoredRule), std::memory_order_relaxed);
                midiNoteHasOverride[index].store (restoredRule != defaultRule, std::memory_order_relaxed);
            }
        }
        else if (state.hasProperty ("enabledNoteMask"))
            setEnabledNoteMask (static_cast<uint16_t> (static_cast<int> (state.getProperty ("enabledNoteMask"))));
        else
            resetNotePolicyToScale (static_cast<int> (parameters.getRawParameterValue ("key")->load()),
                                    static_cast<int> (parameters.getRawParameterValue ("scale")->load()));

        synchronisedPolicyKey = static_cast<int> (parameters.getRawParameterValue ("key")->load (std::memory_order_relaxed));
        synchronisedPolicyScale = static_cast<int> (parameters.getRawParameterValue ("scale")->load (std::memory_order_relaxed));
        notePolicyRevision.fetch_add (1, std::memory_order_relaxed);
    }
}

juce::String VibeAutotuneProcessor::noteNameForMidi (int midiNote)
{
    if (midiNote < 0 || midiNote > 127)
        return "--";

    static constexpr std::array<const char*, 12> names {{ "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B" }};
    return juce::String (names[static_cast<size_t> (midiNote % 12)]) + juce::String (midiNote / 12 - 1);
}

VibeAutotuneProcessor::InputPitchDisplayData VibeAutotuneProcessor::calculateInputPitchDisplay (double stableF0Hz,
                                                                                                   double referenceA4Hz,
                                                                                                   bool voiced) noexcept
{
    InputPitchDisplayData display;
    if (! voiced || ! std::isfinite (stableF0Hz) || stableF0Hz <= 0.0
        || ! std::isfinite (referenceA4Hz) || referenceA4Hz <= 0.0)
        return display;

    const auto midi = 69.0 + 12.0 * std::log2 (stableF0Hz / referenceA4Hz);
    const auto nearestMidi = juce::jlimit (0, 127, static_cast<int> (std::lround (midi)));
    display.midiNote = nearestMidi;
    display.cents = static_cast<float> (juce::jlimit (-100.0, 100.0,
                                                       (midi - static_cast<double> (nearestMidi)) * 100.0));
    return display;
}

void VibeAutotuneProcessor::setMidiTargetNoteFromUi (int midiNote) noexcept
{
    if (midiNote < 0 || midiNote > 127)
    {
        midiTargetNote.store (-1, std::memory_order_relaxed);
        return;
    }

    midiTargetNote.store (midiNote, std::memory_order_relaxed);
}

int VibeAutotuneProcessor::getMidiTargetNote() const noexcept
{
    return midiTargetNote.load (std::memory_order_relaxed);
}

juce::AudioProcessorEditor* VibeAutotuneProcessor::createEditor()
{
    return new VibeAutotuneEditor (*this);
}
