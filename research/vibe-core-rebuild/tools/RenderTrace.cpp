#include "PluginProcessor.h"
#include <juce_audio_formats/juce_audio_formats.h>
#include <chrono>
#include <fstream>
#include <iostream>
#include <memory>

int main(int argc,char** argv) {
    if(argc<3){std::cerr<<"Usage: VibeRenderTrace input.wav output-directory [block=256] [trace=1]\n";return 2;}
    juce::ScopedJuceInitialiser_GUI gui;
    juce::AudioFormatManager formats;formats.registerBasicFormats();
    auto input=juce::File(argv[1]);auto output=juce::File(argv[2]);output.createDirectory();
    std::unique_ptr<juce::AudioFormatReader> reader(formats.createReaderFor(input));
    if(!reader){std::cerr<<"Cannot read input\n";return 2;}
    const int block=argc>3?std::stoi(argv[3]):256;
    const bool trace=argc<=4 || std::stoi(argv[4])!=0;
    const int length=static_cast<int>(reader->lengthInSamples);
    juce::AudioBuffer<float> raw(2,length);reader->read(&raw,0,length,0,true,true);
    if(reader->numChannels==1)raw.copyFrom(1,0,raw,0,0,length);
    auto p=std::make_unique<VibeAutotuneProcessor>();
    for(const auto* id:{"retuneSpeed","flexTune","humanize","naturalVibrato"}) {
        auto* param=p->parameters.getParameter(id);param->setValueNotifyingHost(param->convertTo0to1(0));
    }
    p->prepareToPlay(reader->sampleRate,block);p->setSignalChainDiagnosticEnabled(trace);
    const int total=length+p->getLatencySamples();
    juce::AudioBuffer<float> rendered(2,total),buffer(2,block);juce::MidiBuffer midi;
    std::ofstream csv(output.getChildFile("full_default_intervals.csv").getFullPathName().toStdString());
    csv<<"sampleIndex,sourceSample,observationSample,targetEvent,f0,confidence,ratio,inputCents,targetCents,excitation,synthesis,wet,high,readA,readB,weightA,target,voiced,streamEpoch\n";
    std::array<vibe::TraceEvent,1024> events;
    double maximum=0,totalSeconds=0;
    for(int pos=0;pos<total;pos+=block) {
        const int size=std::min(block,total-pos);buffer.setSize(2,size,false,false,true);buffer.clear();
        const int available=std::max(0,std::min(size,length-pos));
        for(int ch=0;ch<2;++ch) if(available)buffer.copyFrom(ch,0,raw,ch,pos,available);
        const auto start=std::chrono::steady_clock::now();p->processBlock(buffer,midi);
        const double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        maximum=std::max(maximum,elapsed);totalSeconds+=elapsed;
        for(int ch=0;ch<2;++ch)rendered.copyFrom(ch,pos,buffer,ch,0,size);
        const int count=p->copySignalChainDiagnosticFrames(events.data(),static_cast<int>(events.size()));
        for(int i=0;i<count;++i){const auto& e=events[i];
            csv<<e.sampleIndex<<','<<e.sourceSample<<','<<e.observationSample<<','<<e.targetEvent<<','<<e.f0<<','<<e.confidence<<','<<e.ratio<<','<<e.inputCents<<','<<e.targetCents<<','<<e.excitation<<','<<e.synthesis<<','<<e.wet<<','<<e.high<<','<<e.readA<<','<<e.readB<<','<<e.weightA<<','<<e.target<<','<<e.voiced<<','<<e.streamEpoch<<'\n';}
    }
    juce::WavAudioFormat wav;
    auto stream=output.getChildFile("vibe.wav").createOutputStream();
    if(!stream)return 2;
    std::unique_ptr<juce::AudioFormatWriter> writer(wav.createWriterFor(stream.get(),reader->sampleRate,2,24,{},0));
    if(!writer)return 2;stream.release();writer->writeFromAudioSampleBuffer(rendered,0,total);writer.reset();
    std::ofstream report(output.getChildFile("runtime.json").getFullPathName().toStdString());
    report<<"{\"sample_rate\":"<<reader->sampleRate<<",\"latency_samples\":"<<p->getLatencySamples()<<",\"block_size\":"<<block
          <<",\"max_callback_ms\":"<<maximum*1000<<",\"average_cpu_fraction\":"<<totalSeconds/(total/reader->sampleRate)
          <<",\"synthesis_failure_count\":"<<p->getSynthesisFailureCount()<<"}\n";
    std::cout<<"Rendered "<<total<<" samples; synthesis failures="<<p->getSynthesisFailureCount()<<" max_callback_ms="<<maximum*1000<<"\n";
    return p->getSynthesisFailureCount()?1:0;
}
