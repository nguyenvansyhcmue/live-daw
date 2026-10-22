#pragma once
#include "SourceFilterCore.h"
#include <juce_audio_processors/juce_audio_processors.h>
#include <limits>

class VibeAutotuneProcessor : public juce::AudioProcessor {
public:
    struct PitchMonitorData {
        juce::String detectedNote,targetNote,outputNote;
        float inputCents=0,correctionCents=0;
        bool voiced=false,bypassed=false;
    };
    struct InputPitchDisplayData {int midiNote=-1;float cents=0;};
    struct PitchTrackingData {
        double rawF0Hz=0,stableF0Hz=0,confidence=0;
        bool voiced=false;
        uint64_t timestampSamples=0;
        int analysisLatencySamples=0,detectedMidiNote=-1,targetMidiNote=-1,outputMidiNote=-1;
        float inputCents=0,correctionCents=0;
    };
    struct WaveformScopeFrame {
        uint64_t sampleIndex=0;
        float minimum=0,maximum=0,inputPitchCents=0,targetPitchCents=0,deliveredCorrectionCents=0;
        bool voiced=false;
    };
    static constexpr int waveformScopeCapacity=1024;
    using SignalChainDiagnosticFrame=vibe::TraceEvent;
    VibeAutotuneProcessor();
    ~VibeAutotuneProcessor() override=default;
    void prepareToPlay(double,int) override;
    void releaseResources() override {}
    void reset() override;
    void processBlock(juce::AudioBuffer<float>&,juce::MidiBuffer&) override;
    void processBlockBypassed(juce::AudioBuffer<float>&,juce::MidiBuffer&) override;
    bool isBusesLayoutSupported(const BusesLayout&) const override;
    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override{return true;}
    const juce::String getName() const override{return "VibeAutotune";}
    bool acceptsMidi() const override{return false;}
    bool producesMidi() const override{return false;}
    bool isMidiEffect() const override{return false;}
    double getTailLengthSeconds() const override{return getLatencySamples()/std::max(1.,getSampleRate());}
    int getNumPrograms() override{return 1;}
    int getCurrentProgram() override{return 0;}
    void setCurrentProgram(int) override{}
    const juce::String getProgramName(int) override{return {};}
    void changeProgramName(int,const juce::String&) override{}
    void getStateInformation(juce::MemoryBlock&) override;
    void setStateInformation(const void*,int) override;
    juce::AudioProcessorParameter* getBypassParameter() const override;
    PitchMonitorData getPitchMonitorData() const;
    PitchTrackingData getPitchTrackingData() const noexcept;
    static InputPitchDisplayData calculateInputPitchDisplay(double,double,bool) noexcept;
    int copyWaveformScopeFrames(WaveformScopeFrame*,int) const noexcept;
    void setSignalChainDiagnosticEnabled(bool value) noexcept{traceEnabled.store(value);}
    void setLiveDiagnosticCaptureEnabled(bool value) noexcept{setSignalChainDiagnosticEnabled(value);}
    bool isLiveDiagnosticCaptureEnabled() const noexcept{return traceEnabled.load();}
    int copySignalChainDiagnosticFrames(SignalChainDiagnosticFrame*,int) const noexcept;
    int copyLiveDiagnosticFrames(SignalChainDiagnosticFrame* data,int count) const noexcept{return copySignalChainDiagnosticFrames(data,count);}
    uint64_t getSynthesisFailureCount() const noexcept{return synthesisFailures.load();}
    juce::String getLatestDetectedNoteName() const;
    int getLatestDetectedMidiNote() const noexcept;
    int getLatestTargetMidiNote() const noexcept;
    void setMidiTargetNoteFromUi(int) noexcept;
    int getMidiTargetNote() const noexcept;
    uint16_t getEnabledNoteMask() const noexcept;
    void setEnabledNoteMask(uint16_t) noexcept;
    uint16_t getBaseScaleMask() const noexcept;
    bool hasCustomNotePolicy() const noexcept;
    NoteRule getNoteRuleForPitchClass(int) const noexcept;
    NoteRule getNoteRuleForMidiNote(int) const noexcept;
    void setNoteRuleForPitchClass(int,NoteRule) noexcept;
    void setNoteRuleForMidiNote(int,NoteRule) noexcept;
    void resetNoteRuleForPitchClass(int) noexcept;
    void resetNoteRuleForMidiNote(int) noexcept;
    void resetNotePolicyToCurrentScale() noexcept;
    bool getGroupOctaves() const noexcept;
    void setGroupOctaves(bool) noexcept;
    juce::AudioProcessorValueTreeState parameters;
private:
    static juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout();
    static juce::String noteNameForMidi(int);
    static bool scaleContainsPitchClass(int,int,int) noexcept;
    void resetNotePolicyToScale(int,int) noexcept;
    void synchroniseNotePolicyToScale() noexcept;
    NotePolicySnapshot makeNotePolicySnapshot() const noexcept;
    void process(juce::AudioBuffer<float>&,bool);
    void consumeMidi(const juce::MidiBuffer&) noexcept;
    mutable vibe::SourceFilterCore core;
    mutable vibe::TraceQueue<WaveformScopeFrame,waveformScopeCapacity> scope;
    std::array<std::atomic<float>*,10> controlValues{};
    std::atomic<bool> traceEnabled{false};
    std::atomic<uint64_t> synthesisFailures{0};
    std::atomic<int> latestDetectedMidiNote{-1},latestTargetMidiNote{-1},midiTargetNote{-1},latestOutputMidiNote{-1};
    std::atomic<double> latestHz{0},latestConfidence{0};
    std::atomic<float> latestInputCents{0},latestCorrection{0};
    std::atomic<bool> latestVoiced{false},latestBypassed{false};
    std::atomic<uint64_t> latestSample{0};
    std::atomic<uint16_t> enabledNoteMask{0x0fff},baseScaleMask{0x0fff};
    std::array<std::atomic<uint8_t>,12> pitchClassDefaultPolicy{};
    std::array<std::atomic<uint8_t>,128> midiNoteOverridePolicy{};
    std::array<std::atomic<bool>,128> midiNoteHasOverride{};
    std::atomic<bool> groupOctaves{true};
    std::atomic<uint32_t> notePolicyRevision{0};
    int synchronisedPolicyKey=-1,synchronisedPolicyScale=-1;
    int64_t expectedHostSample=-1;
    std::array<bool,128> midiHeldNotes{};
    std::array<uint64_t,128> midiNoteOrder{};
    uint64_t midiOrderCounter=0;
    float scopeMin=0,scopeMax=0;
    int scopeCount=0;
};
