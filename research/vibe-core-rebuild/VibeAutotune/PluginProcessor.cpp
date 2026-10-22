#include "PluginProcessor.h"

VibeAutotuneProcessor::VibeAutotuneProcessor()
    : AudioProcessor(BusesProperties().withInput("Input",juce::AudioChannelSet::stereo(),true)
                                    .withOutput("Output",juce::AudioChannelSet::stereo(),true)),
      parameters(*this,nullptr,"VibeAutotuneState",createParameterLayout()) {
    resetNotePolicyToScale(0,0);
    const char* ids[]{"retuneSpeed","flexTune","humanize","naturalVibrato","tracking","referencePitch","transpose","inputType","bypass","voicedColour"};
    for(size_t i=0;i<controlValues.size();++i)controlValues[i]=parameters.getRawParameterValue(ids[i]);
}
void VibeAutotuneProcessor::prepareToPlay(double rate,int) {
    core.prepare(rate);setLatencySamples(core.getLatencySamples());expectedHostSample=-1;
    midiHeldNotes.fill(false);midiNoteOrder.fill(0);midiOrderCounter=0;
    synchroniseNotePolicyToScale();
}
void VibeAutotuneProcessor::reset(){core.reset();scopeMin=scopeMax=0;scopeCount=0;expectedHostSample=-1;}
void VibeAutotuneProcessor::processBlock(juce::AudioBuffer<float>& b,juce::MidiBuffer& midi){consumeMidi(midi);process(b,false);midi.clear();}
void VibeAutotuneProcessor::processBlockBypassed(juce::AudioBuffer<float>& b,juce::MidiBuffer& midi){process(b,true);midi.clear();}
void VibeAutotuneProcessor::consumeMidi(const juce::MidiBuffer& messages) noexcept {
    // Retained last-held-note priority and CC120/123 flush semantics.
    for(const auto metadata:messages) {
        if(metadata.numBytes>3)continue; // SysEx is unrelated to held-note policy; avoid heap-backed MidiMessage.
        const auto message=metadata.getMessage();
        if(message.isController() && (message.getControllerNumber()==120 || message.getControllerNumber()==123)) {
            midiHeldNotes.fill(false);midiNoteOrder.fill(0);midiTargetNote=-1;
        } else if(message.isNoteOn()) {
            const int note=juce::jlimit(0,127,message.getNoteNumber());
            midiHeldNotes[note]=true;midiNoteOrder[note]=++midiOrderCounter;midiTargetNote=note;
        } else if(message.isNoteOff()) {
            midiHeldNotes[juce::jlimit(0,127,message.getNoteNumber())]=false;
            int next=-1;uint64_t newest=0;
            for(int note=0;note<128;++note)if(midiHeldNotes[note] && midiNoteOrder[note]>newest){newest=midiNoteOrder[note];next=note;}
            midiTargetNote=next;
        }
    }
}
void VibeAutotuneProcessor::process(juce::AudioBuffer<float>& b,bool hostBypass) {
    juce::ScopedNoDenormals noDenormals;
    const auto count=b.getNumSamples();if(count==0)return;
    for(int ch=getTotalNumInputChannels();ch<b.getNumChannels();++ch)b.clear(ch,0,count);
    if(b.getNumChannels()==0)return;
    if(auto* playhead=getPlayHead())if(auto position=playhead->getPosition())if(auto sample=position->getTimeInSamples()) {
        if(position->getIsPlaying()) {
            if(expectedHostSample>=0 && *sample!=expectedHostSample)core.reset();
            expectedHostSample=*sample+count;
        } else expectedHostSample=-1;
    }
    synchroniseNotePolicyToScale();const auto policy=makeNotePolicySnapshot();
    auto value=[&](int i){return static_cast<double>(controlValues[i]->load(std::memory_order_relaxed));};
    vibe::Controls c;c.retune=value(0);c.flex=value(1);c.humanize=value(2);c.vibrato=value(3);
    c.tracking=value(4);c.reference=value(5);c.transpose=static_cast<int>(value(6));c.voice=static_cast<int>(value(7));
    c.bypass=hostBypass || value(8)>=.5;c.colour=value(9);
    core.traceEnabled=traceEnabled.load(std::memory_order_relaxed);
    const auto start=core.getSampleIndex();
    core.process(b.getArrayOfWritePointers(),count,b.getNumChannels(),c,policy);
    const auto d=core.latest;
    const auto display=calculateInputPitchDisplay(d.f0,c.reference,d.voiced);
    latestDetectedMidiNote=display.midiNote;latestTargetMidiNote=d.target;
    latestOutputMidiNote=d.voiced?static_cast<int>(std::lround(69+12*std::log2(d.f0*d.ratio/c.reference))):-1;
    latestHz=d.f0;latestConfidence=d.confidence;latestVoiced=d.voiced;latestBypassed=c.bypass;
    latestInputCents=display.cents;latestCorrection=static_cast<float>(1200*std::log2(d.ratio));latestSample=core.getSampleIndex();
    synthesisFailures=core.failures;
    for(int n=0;n<count;++n) {
        const float x=b.getSample(0,n);scopeMin=std::min(scopeMin,x);scopeMax=std::max(scopeMax,x);
        if(++scopeCount==128) {
            scope.push({start+static_cast<uint64_t>(n),scopeMin,scopeMax,static_cast<float>(d.inputCents),
                        static_cast<float>(d.targetCents),latestCorrection.load(),d.voiced});
            scopeCount=0;scopeMin=scopeMax=0;
        }
    }
}
int VibeAutotuneProcessor::copyWaveformScopeFrames(WaveformScopeFrame* output,int capacity) const noexcept {
    int n=0;while(n<capacity && scope.pop(output[n]))++n;return n;
}
int VibeAutotuneProcessor::copySignalChainDiagnosticFrames(SignalChainDiagnosticFrame* output,int capacity) const noexcept {
    int n=0;while(n<capacity && core.trace.pop(output[n]))++n;return n;
}
VibeAutotuneProcessor::PitchMonitorData VibeAutotuneProcessor::getPitchMonitorData() const {
    return {noteNameForMidi(latestDetectedMidiNote.load()),noteNameForMidi(latestTargetMidiNote.load()),
            noteNameForMidi(latestOutputMidiNote.load()),latestInputCents.load(),latestCorrection.load(),latestVoiced.load(),latestBypassed.load()};
}
VibeAutotuneProcessor::PitchTrackingData VibeAutotuneProcessor::getPitchTrackingData() const noexcept {
    PitchTrackingData d;d.rawF0Hz=d.stableF0Hz=latestHz.load();d.confidence=latestConfidence.load();d.voiced=latestVoiced.load();
    d.timestampSamples=latestSample.load();d.analysisLatencySamples=getLatencySamples();
    d.detectedMidiNote=latestDetectedMidiNote.load();d.targetMidiNote=latestTargetMidiNote.load();d.outputMidiNote=latestOutputMidiNote.load();
    d.inputCents=latestInputCents.load();d.correctionCents=latestCorrection.load();return d;
}
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter(){return new VibeAutotuneProcessor();}
