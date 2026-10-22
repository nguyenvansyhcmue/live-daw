#include "Services/StudioForgeCalibrationRunner.h"
#include <juce_gui_basics/juce_gui_basics.h>
#include <AudioToolbox/AudioToolbox.h>
#include <CoreFoundation/CoreFoundation.h>
#include <iostream>

// Optional in-process registration using the public AU factory advertised
// by the bundle. Does not install, patch, sign, or alter Artist licensing.
static bool registerBundle(const char* path) {
    const auto url=CFURLCreateFromFileSystemRepresentation(nullptr,reinterpret_cast<const UInt8*>(path),std::strlen(path),true);
    if(!url)return false;
    const auto bundle=CFBundleCreate(nullptr,url);CFRelease(url);if(!bundle)return false;
    const auto info=CFBundleGetInfoDictionary(bundle);
    const auto components=static_cast<CFArrayRef>(CFDictionaryGetValue(info,CFSTR("AudioComponents")));
    if(!components || !CFArrayGetCount(components))return false;
    const auto entry=static_cast<CFDictionaryRef>(CFArrayGetValueAtIndex(components,0));
    auto fourcc=[&](CFStringRef name){
        char text[32]{};auto str=static_cast<CFStringRef>(CFDictionaryGetValue(entry,name));
        if(!str || !CFStringGetCString(str,text,sizeof(text),kCFStringEncodingASCII))return UInt32(0);
        return UInt32(static_cast<unsigned char>(text[0]))<<24 | UInt32(static_cast<unsigned char>(text[1]))<<16
              | UInt32(static_cast<unsigned char>(text[2]))<<8 | UInt32(static_cast<unsigned char>(text[3]));
    };
    const auto name=static_cast<CFStringRef>(CFDictionaryGetValue(entry,CFSTR("name")));
    const auto factoryName=static_cast<CFStringRef>(CFDictionaryGetValue(entry,CFSTR("factoryFunction")));
    if(!factoryName)return false;
    auto factory=reinterpret_cast<AudioComponentFactoryFunction>(CFBundleGetFunctionPointerForName(bundle,factoryName));
    if(!factory)return false;
    AudioComponentDescription d{fourcc(CFSTR("type")),fourcc(CFSTR("subtype")),fourcc(CFSTR("manufacturer")),0,0};
    SInt32 version=0;auto number=static_cast<CFNumberRef>(CFDictionaryGetValue(entry,CFSTR("version")));
    if(number)CFNumberGetValue(number,kCFNumberSInt32Type,&version);
    auto registered=AudioComponentRegister(&d,name,static_cast<UInt32>(version),factory);
    // The bundle intentionally remains loaded for the lifetime of the host.
    return registered!=nullptr;
}
int main(int argc,char** argv){
    if(argc<4){std::cerr<<"Usage: StudioForgeReferenceRunner input output query [vst3]\n";return 2;}
    juce::ScopedJuceInitialiser_GUI gui;
    if(const char* bundle=std::getenv("VIBE_REFERENCE_AU_BUNDLE")) {
        if(!registerBundle(bundle)){std::cerr<<"Cannot register the AU factory in this process\n";return 3;}
    }
    StudioForgeCalibrationRunner::Request request;
    request.input=juce::File(argv[1]);request.outputDirectory=juce::File(argv[2]);request.pluginQuery=argv[3];
    if(argc>4)request.pluginPath=juce::File(argv[4]);
    request.cases={{0,0,0,0}};
    if(std::getenv("VIBE_REFERENCE_ALL_CONTROLS")) {
        for(float x:{10.f,25.f,50.f,100.f})request.cases.push_back({x,0,0,0});
        for(float x:{25.f,50.f,75.f,100.f})request.cases.push_back({0,x,0,0});
        for(float x:{25.f,50.f,75.f,100.f})request.cases.push_back({0,0,x,0});
        for(float x:{-12.f,-9.f,-6.f,3.f,6.f,9.f,12.f})request.cases.push_back({0,0,0,x});
    }
    juce::String report;
    if(auto result=StudioForgeCalibrationRunner::run(request,report);result.failed()){std::cerr<<result.getErrorMessage()<<'\n';return 1;}
    request.outputDirectory.getChildFile("calibration-report.csv").replaceWithText(report);
    std::cout<<report;
}
