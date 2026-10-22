#include "SourceFilterCore.h"
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <random>
#include <stdexcept>

static bool trackAllocations=false;
static size_t allocations=0;
void* operator new(std::size_t size) {if(trackAllocations)++allocations;if(auto p=std::malloc(size?size:1))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}
void* operator new[](std::size_t s){return ::operator new(s);}
void operator delete[](void* p) noexcept{std::free(p);}

void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
std::vector<float> fixture(double rate,int length) {
    std::vector<float> x(length);std::mt19937 rng(42);std::uniform_real_distribution<double> random(-1,1);
    double phase=0;
    for(int n=0;n<length;++n) {
        double time=n/rate;
        double hz=time<.7?220:time<1.2?246.94165:196;
        phase+=2*vibe::pi*hz/rate;
        double noise=(time>.95 && time<1.05)? .04*random(rng):0;
        x[n]=static_cast<float>((.15*std::sin(phase)+.06*std::sin(2*phase)+.03*std::sin(5*phase)+noise)*std::min(1.,time/.01));
    }
    return x;
}
std::vector<float> run(const std::vector<float>& input,double rate,int block,bool trace,bool bypass=false,double ratio=0) {
    auto core=std::make_unique<vibe::SourceFilterCore>();core->prepare(rate);core->traceEnabled=trace;
    if(ratio>0) {vibe::Decision d;d.f0=220;d.ratio=ratio;d.voiced=true;d.confidence=1;d.target=57;core->setTestControl(d);}
    auto output=input;
    NotePolicySnapshot policy;policy.pitchClassDefaults.fill(NoteRule::Legal);
    vibe::Controls controls;controls.retune=0;controls.bypass=bypass;
    auto start=std::chrono::steady_clock::now();
    trackAllocations=true;
    for(int i=0;i<static_cast<int>(output.size());i+=block) {
        float* data[]{output.data()+i};core->process(data,std::min(block,static_cast<int>(output.size())-i),1,controls,policy);
    }
    trackAllocations=false;
    const auto elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    require(core->failures==0,"Synthesis stability guard fired");
    require(allocations==0,"Allocation in core process");
    for(float x:output) require(std::isfinite(x),"Non-finite output");
    std::cout<<"render | rate="<<rate<<" block="<<block<<" latency="<<core->getLatencySamples()<<" cpu_fraction="<<elapsed/(input.size()/rate)<<"\n";
    return output;
}
double pitch(const std::vector<float>& x,double rate,int start,int length) {
    double best=-1;int bestLag=0;
    std::vector<double> corr(400);
    for(int lag=120;lag<350;++lag) {
        double cross=0,a=0,b=0;
        for(int i=start;i<start+length;++i){cross+=x[i]*x[i+lag];a+=x[i]*x[i];b+=x[i+lag]*x[i+lag];}
        corr[lag]=cross/std::sqrt(a*b+1e-30);
        if(corr[lag]>best){best=corr[lag];bestLag=lag;}
    }
    double f=.5*(corr[bestLag-1]-corr[bestLag+1])/(corr[bestLag-1]-2*corr[bestLag]+corr[bestLag+1]);
    return rate/(bestLag+f);
}
int main(){try{
    for(double rate:{44100.,48000.,96000.}){
        auto x=fixture(rate,static_cast<int>(rate*1.5));
        auto unity=run(x,rate,256,false,true);
        auto core=std::make_unique<vibe::SourceFilterCore>();core->prepare(rate);int latency=core->getLatencySamples();
        double error=0;
        for(size_t i=latency;i<x.size();++i) error=std::max(error,std::abs(double(unity[i]-x[i-latency])));
        std::cout<<"lpc_identity | max_error="<<error<<"\n";require(error<2e-5,"LPC reconstruction not transparent");
    }
    auto input=fixture(48000,72000);
    auto baseline=run(input,48000,256,false);
    for(int block:{1,64,128,1024})require(run(input,48000,block,false)==baseline,"Host block changes audio");
    require(run(input,48000,256,true)==baseline,"Trace changes audio");
    std::vector<float> harmonic(96000);
    for(size_t n=0;n<harmonic.size();++n) {double p=2*vibe::pi*220*n/48000;harmonic[n]=float(.2*std::sin(p)+.05*std::sin(3*p));}
    for(double ratio:{.9438743127,1.,1.059463094}) {
        auto rendered=run(harmonic,48000,256,false,false,ratio);
        double measured=pitch(rendered,48000,40000,4096);
        double cents=1200*std::log2(measured/(220*ratio));
        std::cout<<"pitch_delivery | ratio="<<ratio<<" measured="<<measured<<" error_cents="<<cents<<"\n";
        require(std::abs(cents)<5,"Pitch shifter does not reach target");
    }
    NotePolicySnapshot policy;policy.pitchClassDefaults.fill(NoteRule::IllegalNearest);
    for(int pc:{0,2,4,5,7,9,11})policy.pitchClassDefaults[pc]=NoteRule::Legal;
    require(MusicalPolicy::nearestLegalNote(61,policy,-1)==60,"Tie-break changed");
    require(MusicalPolicy::selectPolicyTarget(61,NoteRule::IllegalUp,policy,-1)==62,"Up policy changed");
    require(MusicalPolicy::selectPolicyTarget(61,NoteRule::IllegalDown,policy,-1)==60,"Down policy changed");
    // Public-control behaviour on an independent sustained vibrato, separate
    // from any recorded singer or reference pitch trajectory.
    auto controlMotion=[&](double retune,double flex,double humanize,double natural){
        vibe::ControlTrajectory trajectory;trajectory.prepare(48000);
        vibe::Controls controls;controls.retune=retune;controls.flex=flex;controls.humanize=humanize;controls.vibrato=natural;
        NotePolicySnapshot held;held.midiTargetNote=57;
        double power=0;int count=0;
        for(int n=0;n<96000;n+=64){
            const double cents=25*std::sin(2*vibe::pi*6*n/48000.);
            vibe::Observation o;o.hz=220*std::exp2(cents/1200);o.confidence=1;o.voiced=true;o.sourceSample=n;
            const auto d=trajectory.update(o,controls,held);
            if(n>48000){double delivered=cents+1200*std::log2(d.ratio);power+=delivered*delivered;++count;}
        }
        return std::sqrt(power/count);
    };
    const double hard=controlMotion(0,0,0,0),slow=controlMotion(50,0,0,0);
    const double flex=controlMotion(0,100,0,0),human=controlMotion(0,0,100,0);
    const double down=controlMotion(50,0,0,-12),up=controlMotion(50,0,0,12);
    std::cout<<"controls | hard="<<hard<<" slow="<<slow<<" flex="<<flex<<" human="<<human<<" vibrato_down="<<down<<" up="<<up<<"\n";
    require(hard<1e-6 && slow>5 && flex>2 && human>5,"Control is inert or hard tune misses note centre");
    require(down<slow && up>slow,"Natural Vibrato direction incorrect");
    // Exercise reset, saturation, weak F0 and control/bypass changes. This is
    // numerical safety evidence, not a subjective click-free quality verdict.
    {
        auto core=std::make_unique<vibe::SourceFilterCore>();core->prepare(48000);
        std::array<float,128> left{},right{};
        float* channels[]{left.data(),right.data()};
        std::mt19937 random(101);std::uniform_real_distribution<float> noise(-.2f,.2f);
        vibe::Controls controls;controls.retune=0;
        double peak=0;
        for(int block=0;block<1000;++block){
            if(block==500)core->reset();
            controls.bypass=(block/50)%2;
            controls.retune=(block%3)*200;controls.flex=(block%3)*50;
            controls.humanize=(block%3)*50;controls.vibrato=(block%3-1)*12;
            for(int n=0;n<128;++n){
                const double t=(block*128+n)/48000.;
                left[n]=float(.16*std::sin(2*vibe::pi*(100+180*t)*t))+noise(random)*((block/20)%2);
                right[n]=left[n]*.7f;
            }
            if(block==300)left[0]=std::numeric_limits<float>::quiet_NaN();
            if(block==301)right[0]=std::numeric_limits<float>::infinity();
            trackAllocations=true;core->process(channels,128,2,controls,policy);trackAllocations=false;
            for(int n=0;n<128;++n){
                require(std::isfinite(left[n])&&std::isfinite(right[n]),"Non-finite stereo/control output");
                peak=std::max({peak,std::abs(double(left[n])),std::abs(double(right[n]))});
            }
            require(core->failures==0,"Dynamic control/reset caused synthesis instability");
        }
        require(allocations==0,"Control changes allocated");
        require(peak<2,"Dynamic control/reset produced an excessive peak");
        std::cout<<"dynamic_safety | stereo=pass NaN_Inf=pass reset=pass peak="<<peak<<"\n";
    }
    std::cout<<"PASS: source/filter identity, pitch delivery, block/trace invariance, musical policy, no allocations\n";
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}}
