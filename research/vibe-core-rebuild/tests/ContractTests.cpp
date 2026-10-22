#include "PluginProcessor.h"
#include <iostream>
#include <memory>
#include <stdexcept>
static void check(bool condition,const char* message){if(!condition)throw std::runtime_error(message);}
int main(){juce::ScopedJuceInitialiser_GUI gui;try{
    auto p=std::make_unique<VibeAutotuneProcessor>();
    check(p->parameters.getParameter("retuneSpeed")->getNormalisableRange().end==400,"Retune range");
    check(p->parameters.getParameter("naturalVibrato")->getNormalisableRange().start==-12,"Vibrato range");
    p->prepareToPlay(48000,256);
    check(p->getBaseScaleMask()==0x0b56,"F# Natural Minor mask");
    p->setGroupOctaves(false);p->setNoteRuleForMidiNote(61,NoteRule::IllegalDown);
    p->setMidiTargetNoteFromUi(64);check(p->getMidiTargetNote()==64,"UI MIDI target");
    juce::MemoryBlock state;p->getStateInformation(state);
    auto q=std::make_unique<VibeAutotuneProcessor>();q->setStateInformation(state.getData(),static_cast<int>(state.getSize()));
    q->prepareToPlay(48000,256);
    check(q->getNoteRuleForMidiNote(61)==NoteRule::IllegalDown,"MIDI override persistence");
    check(!q->getGroupOctaves(),"Octave grouping persistence");
    check(*q->parameters.getRawParameterValue("key")==6,"Key persistence");
    check(*q->parameters.getRawParameterValue("scale")==2,"Scale persistence");
    juce::AudioBuffer<float> audio(2,256);juce::MidiBuffer midi;
    audio.clear();midi.addEvent(juce::MidiMessage::noteOn(1,60,0.8f),0);p->processBlock(audio,midi);check(p->getMidiTargetNote()==60,"MIDI note-on");
    midi.addEvent(juce::MidiMessage::noteOn(1,64,0.8f),0);p->processBlock(audio,midi);check(p->getMidiTargetNote()==64,"Last-held priority");
    midi.addEvent(juce::MidiMessage::noteOff(1,64),0);p->processBlock(audio,midi);check(p->getMidiTargetNote()==60,"MIDI note-off restores held note");
    midi.addEvent(juce::MidiMessage::controllerEvent(1,123,0),0);p->processBlock(audio,midi);check(p->getMidiTargetNote()==-1,"MIDI all-notes-off");
    for(int i=0;i<50;++i){audio.clear();p->processBlock(audio,midi);}
    p->reset();p->prepareToPlay(44100,64);audio.setSize(2,64);audio.clear();p->processBlockBypassed(audio,midi);
    check(p->getSynthesisFailureCount()==0,"Reset/reprepare stability");
    auto editor=std::unique_ptr<juce::AudioProcessorEditor>(p->createEditor());check(editor!=nullptr,"Preserved UI creation");
    std::cout<<"PASS: parameters, scale, note map, state, MIDI UI, bypass/reset/reprepare, editor\n";
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}}
