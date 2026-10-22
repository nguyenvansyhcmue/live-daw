#pragma once
#include "MusicalPolicy.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <vector>

namespace vibe {
constexpr double pi = 3.14159265358979323846;
constexpr int order = 20;
using Coefficients = std::array<double, order + 1>;

// SPSC ownership: the producer never overwrites an unread slot. Payload
// publication and slot reuse both use release/acquire. Overflow drops a
// diagnostic event, never an audio sample.
template<class T, size_t N> class TraceQueue {
public:
    bool push(const T& x) noexcept {
        auto w = write.load(std::memory_order_relaxed);
        auto next = (w + 1) % N;
        if (next == read.load(std::memory_order_acquire)) { ++dropped; return false; }
        slots[w] = x; write.store(next, std::memory_order_release); return true;
    }
    bool pop(T& x) noexcept {
        auto r = read.load(std::memory_order_relaxed);
        if (r == write.load(std::memory_order_acquire)) return false;
        x = slots[r]; read.store((r + 1) % N, std::memory_order_release); return true;
    }
    void reset() noexcept { read = 0; write = 0; dropped = 0; }
    std::atomic<uint64_t> dropped {0};
private:
    std::array<T,N> slots {};
    std::atomic<size_t> read {0}, write {0};
};

// Autocorrelation LPC with diagonal loading and bounded reflection
// coefficients. A(z)=1+sum(a[k]z^-k); analysis e=A(z)x, synthesis y=e/A(z).
// The coefficients are shared by analysis/synthesis at the same source time.
class Envelope {
public:
    void prepare(int length) {
        window.resize(static_cast<size_t>(length));
        frame.resize(window.size());
        for (int i=0;i<length;++i) window[i]=0.5-0.5*std::cos(2*pi*i/(length-1));
    }
    template<class Reader> Coefficients analyse(Reader sample, int64_t end) noexcept {
        Coefficients a {}; a[0]=1;
        std::array<double,order+1> r {};
        double mean=0;
        for(size_t i=0;i<frame.size();++i) mean+=sample(end-static_cast<int64_t>(frame.size())+1+i);
        mean/=frame.size();
        for(size_t i=0;i<frame.size();++i)
            frame[i]=(sample(end-static_cast<int64_t>(frame.size())+1+i)-mean)*window[i];
        for(int k=0;k<=order;++k)
            for(size_t i=k;i<frame.size();++i) r[k]+=frame[i]*frame[i-k];
        if(r[0]<1e-12) return a;
        r[0]*=1.0001;
        double error=r[0];
        for(int m=1;m<=order;++m) {
            double sum=r[m];
            for(int j=1;j<m;++j) sum+=a[j]*r[m-j];
            const double reflection=std::clamp(-sum/std::max(error,1e-20),-.98,.98);
            const auto previous=a;
            for(int j=1;j<m;++j) a[j]=previous[j]+reflection*previous[m-j];
            a[m]=reflection;
            error*=1-reflection*reflection;
        }
        // Pole-radius contraction supplies a bounded envelope and reduces
        // pitch-harmonic imprint without an output EQ or an amplitude gate.
        double bandwidth=1;
        for(int j=1;j<=order;++j) { bandwidth*=.996; a[j]*=bandwidth; }
        return a;
    }
private:
    std::vector<double> window,frame;
};

struct Observation { double hz=0, confidence=0, rms=0, high=0; bool voiced=false; int64_t sourceSample=0; };
class PitchObserver {
public:
    void prepare(double fs) {
        rate=fs; decimation=std::max(1,static_cast<int>(std::lround(fs/12000.0)));
        internalRate=fs/decimation; filterAlpha=1-std::exp(-2*pi*1800/fs); reset();
    }
    void reset() noexcept { ring.fill(0); position=count=tick=0; low1=low2=0; observation={}; }
    bool push(double input, int64_t sampleIndex, int voice, double tracking) noexcept {
        low1+=filterAlpha*(input-low1); low2+=filterAlpha*(low1-low2);
        if(++tick<decimation) return false;
        tick=0; ring[position%512]=low2; ++position;
        if(++count<16 || position<512) return false;
        count=0;
        constexpr double mins[] {150,85,65,45}, maxs[] {1200,850,650,450};
        const int minLag=std::max(2,static_cast<int>(internalRate/maxs[std::clamp(voice,0,3)]));
        const int maxLag=std::min(255,static_cast<int>(internalRate/mins[std::clamp(voice,0,3)]));
        std::array<double,257> difference{}, cmnd{};
        auto at=[&](int offset){return ring[(position-1-offset)%512];};
        double energy=0;
        for(int j=0;j<256;++j) energy+=at(j)*at(j);
        double cumulative=0;
        for(int lag=1;lag<=maxLag;++lag) {
            double sum=0;
            for(int j=0;j<256;++j) {double d=at(j)-at(j+lag); sum+=d*d;}
            difference[lag]=sum; cumulative+=sum;
            cmnd[lag]=sum*lag/std::max(cumulative,1e-24);
        }
        int best=-1;
        const double threshold=.08+.12*std::clamp(tracking/100.,0.,1.);
        for(int lag=minLag;lag<maxLag;++lag) {
            if(cmnd[lag]<threshold && cmnd[lag]<=cmnd[lag-1] && cmnd[lag]<cmnd[lag+1]) {best=lag;break;}
        }
        if(best<0) {
            best=minLag;
            for(int lag=minLag+1;lag<maxLag;++lag) if(cmnd[lag]<cmnd[best]) best=lag;
        }
        double fraction=0;
        if(best>1 && best<maxLag) {
            double denom=cmnd[best-1]-2*cmnd[best]+cmnd[best+1];
            if(std::abs(denom)>1e-12) fraction=std::clamp(.5*(cmnd[best-1]-cmnd[best+1])/denom,-.5,.5);
        }
        observation.hz=internalRate/(best+fraction);
        observation.confidence=std::clamp(1-cmnd[best],0.,1.);
        observation.rms=std::sqrt(energy/256);
        observation.voiced=observation.rms>1e-5 && observation.confidence>1-threshold;
        // Centre of the actual compared data, not merely the end of the callback.
        observation.sourceSample=sampleIndex-(128+best/2)*decimation;
        return true;
    }
    Observation observation;
private:
    std::array<double,512> ring{};
    uint64_t position=0;
    int count=0,tick=0,decimation=4;
    double rate=48000,internalRate=12000,low1=0,low2=0,filterAlpha=0;
};

struct Controls {
    double retune=100, flex=0, humanize=0, vibrato=0, tracking=50, reference=440, colour=0;
    int transpose=0,voice=1;
    bool bypass=false;
};
struct Decision {
    int64_t sourceSample=0;
    uint64_t event=0;
    double f0=0, confidence=0, ratio=1, inputCents=0,targetCents=0;
    int target=-1;
    bool voiced=false;
};
class ControlTrajectory {
public:
    void prepare(double fs) noexcept { rate=fs; reset(); }
    void reset() noexcept { current={}; correction=centre=vibratoLow=0; initial=true; heldSamples=0; }
    Decision update(const Observation& o,const Controls& c,const NotePolicySnapshot& policy) noexcept {
        const auto delta=std::max<int64_t>(1,o.sourceSample-current.sourceSample);
        const double dt=delta/rate;
        current.sourceSample=o.sourceSample; current.f0=o.hz; current.confidence=o.confidence;
        current.voiced=o.voiced; current.ratio=1;
        if(!o.voiced || o.hz<=0) {initial=true;heldSamples=0;return current;}
        const double midi=69+12*std::log2(o.hz/c.reference);
        current.inputCents=100*(midi-69);
        auto sourceRule=policy.ruleForMidi(std::clamp(static_cast<int>(std::lround(midi)),0,127));
        int selected=policy.midiTargetNote>=0 ? policy.midiTargetNote
          : MusicalPolicy::selectPolicyTarget(midi+c.transpose,sourceRule,policy,current.target);
        if(selected!=current.target) {++current.event; heldSamples=0;}
        else heldSamples+=delta;
        current.target=selected;
        current.targetCents=100*(selected-69);
        if(selected<0 || (policy.midiTargetNote<0 && sourceRule==NoteRule::BypassLegal)) return current;
        double desired=current.targetCents-current.inputCents;
        // Flex relaxes correction near a target; it never changes scale membership.
        const double flexWidth=.5*c.flex;
        if(flexWidth>0) desired*=std::clamp(std::abs(desired)/flexWidth,0.,1.);
        if(initial) {centre=current.inputCents;vibratoLow=0;correction=0;initial=false;}
        centre+=(current.inputCents-centre)*(1-std::exp(-dt/.10));
        const double deviation=current.inputCents-centre;
        vibratoLow+=(deviation-vibratoLow)*(1-std::exp(-dt/.012));
        const double sustain=std::clamp((heldSamples/rate-.12)/.18,0.,1.);
        // Milliseconds are a time constant. Zero is an explicit direct control
        // write; continuity is provided by the synthesis state, not ratio slewing.
        const double tau=c.retune*.001+.040*(c.humanize*.01)*sustain;
        correction+=(desired-correction)*(tau<=0?1:1-std::exp(-dt/tau));
        const double retention=std::clamp(1-std::exp(-tau/.040)+c.flex*.01,0.,1.);
        const double natural=std::clamp(vibratoLow,-60.,60.)*(c.vibrato/12.)*(c.vibrato<0?retention:1.);
        current.ratio=std::exp2(std::clamp(correction+natural,-1200.,1200.)/1200.);
        return current;
    }
    Decision current;
private:
    double rate=48000,correction=0,centre=0,vibratoLow=0;
    bool initial=true;
    int64_t heldSamples=0;
};

struct TraceEvent {
    uint64_t sampleIndex=0;
    int64_t sourceSample=0,observationSample=0;
    uint64_t targetEvent=0;
    double f0=0,confidence=0,ratio=1,inputCents=0,targetCents=0;
    double excitation=0,synthesis=0,wet=0,high=0,readA=0,readB=0,weightA=0;
    int target=-1;
    bool voiced=false;
    uint64_t streamEpoch=0;
};

// A single source/filter synthesis path. Two bounded fractional reads of the
// LPC residual share a period-sized separation and complementary windows.
// There are no detected epochs, source-mark queues or scheduled OLA grains.
// At ratio=1 the primary read is exactly on the nominal source time.
class SourceFilterCore {
public:
    static constexpr size_t traceCapacity=16384;
    void prepare(double fs) {
        rate=fs;
        envelopeLength=static_cast<int>(std::lround(fs*.024));
        analysisDelay=envelopeLength/2;
        synthesisDelay=static_cast<int>(std::ceil(fs/40.0))+4;
        latency=analysisDelay+synthesisDelay;
        length=1;while(length<latency*4+envelopeLength+128) length*=2;
        mask=length-1;
        for(auto& channel:channels) {
            channel.input.assign(length,0);channel.residual.assign(length,0);
            channel.coefficients.assign(length,Coefficients{});
            channel.envelope.prepare(envelopeLength);
        }
        decisions.assign(length,Decision{}); highEvidence.assign(length,0);
        observer.prepare(fs);trajectory.prepare(fs); reset();
    }
    void reset() noexcept {
        clock=0; phase=.5;period=rate/220;wet=0;low=highEnergy=totalEnergy=0;
        failures=0; observer.reset();trajectory.reset();++streamEpoch;
        // The consumer may be draining trace during a host seek/reset. Do not
        // reset its read index from the audio thread. Epoch separates runs.
        for(auto& ch:channels) {
            std::fill(ch.input.begin(),ch.input.end(),0);std::fill(ch.residual.begin(),ch.residual.end(),0);
            ch.a={};ch.a[0]=1;ch.history={};
            for(auto& a:ch.coefficients) {a={};a[0]=1;}
        }
        std::fill(decisions.begin(),decisions.end(),Decision{});
        std::fill(highEvidence.begin(),highEvidence.end(),0);
    }
    void process(float* const* data,int count,int channelCount,const Controls& c,const NotePolicySnapshot& policy) noexcept {
        const int nc=std::clamp(channelCount,1,2);
        for(int n=0;n<count;++n,++clock) {
            double mono=0;
            for(int ch=0;ch<nc;++ch) {
                const double x=std::isfinite(data[ch][n])?data[ch][n]:0;
                channels[ch].input[index(clock)]=x;mono+=x/nc;
            }
            const double lowAlpha=1-std::exp(-2*pi*3000/rate);
            low+=lowAlpha*(mono-low);
            const double energyAlpha=1-std::exp(-1/(rate*.001));
            totalEnergy+=energyAlpha*(mono*mono-totalEnergy);
            highEnergy+=energyAlpha*((mono-low)*(mono-low)-highEnergy);
            highEvidence[index(clock)]=highEnergy/std::max(totalEnergy,1e-12);
            if(observer.push(mono,clock,c.voice,c.tracking)) {
                const auto next=trajectory.update(observer.observation,c,policy);
                // Write retroactively only into still-unrendered source history.
                // The fixed synthesis delay exceeds observation support.
                for(auto s=std::max<int64_t>(0,next.sourceSample);s<=clock;++s) decisions[index(s)]=next;
            } else decisions[index(clock)]=trajectory.current;

            const int64_t residualTime=clock-analysisDelay;
            for(int ch=0;ch<nc;++ch) {
                auto& channel=channels[ch];
                if(clock%128==0) channel.a=channel.envelope.analyse([&](int64_t s){return read(channel.input,s);},clock);
                double excitation=read(channel.input,residualTime);
                for(int k=1;k<=order;++k) excitation+=channel.a[k]*read(channel.input,residualTime-k);
                if(residualTime>=0) {
                    channel.residual[index(residualTime)]=excitation;
                    channel.coefficients[index(residualTime)]=channel.a;
                }
            }
            const int64_t source=clock-latency;
            Decision decision=source>=0?decisions[index(source)]:Decision{};
            if(testControlEnabled) decision=testDecision;
            const double high=source>=0?highEvidence[index(source)]:0;
            const bool valid=decision.voiced && decision.f0>=40 && decision.f0<=1500 && !c.bypass;
            const double targetPeriod=valid?rate/decision.f0:period;
            period+=(std::clamp(targetPeriod,rate/1500,rate/40)-period)*(1-std::exp(-1/(rate*.005)));
            const double ratio=valid?decision.ratio:1;
            phase+=(ratio-1)/(2*period);phase-=std::floor(phase);
            double other=phase+.5;other-=std::floor(other);
            const double readA=source+(phase-.5)*2*period,readB=source+(other-.5)*2*period;
            const double w=.5-.5*std::cos(2*pi*phase);
            const double wetTarget=valid?std::clamp((.65-high)/.35,0.,1.):0;
            wet+=(wetTarget-wet)*(1-std::exp(-1/(rate*(wetTarget<wet?.002:.004))));
            double lastExcitation=0,lastSynthesis=0;
            for(int ch=0;ch<nc;++ch) {
                auto& channel=channels[ch];
                const auto a=source>=0?channel.coefficients[index(source)]:identity();
                const double shifted=w*interpolate(channel.residual,readA)+(1-w)*interpolate(channel.residual,readB);
                const double aligned=read(channel.residual,source);
                // Crossfade in excitation space; the envelope filter runs
                // continuously through consonants and bypass transitions.
                const double e=aligned+(shifted-aligned)*wet;
                double y=e;
                for(int k=1;k<=order;++k) y-=a[k]*channel.history[k-1];
                if(!std::isfinite(y) || std::abs(y)>8) {++failures;y=read(channel.input,source);channel.history={};}
                for(int k=order-1;k>0;--k) channel.history[k]=channel.history[k-1];
                channel.history[0]=y;
                const double colour=std::clamp(c.colour*.01,0.,1.)*wet;
                const double drive=1+2.5*colour;
                data[ch][n]=static_cast<float>(y+(std::tanh(y*drive)/drive-y)*(.18*colour));
                lastExcitation=e;lastSynthesis=y;
            }
            if(traceEnabled && clock%64==0)
                trace.push({static_cast<uint64_t>(clock),source,decision.sourceSample,decision.event,
                  decision.f0,decision.confidence,ratio,decision.inputCents,decision.targetCents,
                  lastExcitation,lastSynthesis,wet,high,readA,readB,w,decision.target,decision.voiced,streamEpoch});
            latest=decision; latestWet=wet;
        }
    }
    int getLatencySamples() const noexcept{return latency;}
    uint64_t getSampleIndex() const noexcept{return static_cast<uint64_t>(clock);}
    uint64_t failures=0;
    bool traceEnabled=false;
    TraceQueue<TraceEvent,traceCapacity> trace;
    Decision latest;
    double latestWet=0;
    // Synthetic fixture input, never exposed as a plug-in parameter or engine switch.
    void setTestControl(Decision value) noexcept{testDecision=value;testControlEnabled=true;}
private:
    struct Channel {
        std::vector<double> input,residual;
        std::vector<Coefficients> coefficients;
        std::array<double,order> history{};
        Coefficients a{};
        Envelope envelope;
    };
    static Coefficients identity() noexcept{Coefficients a{};a[0]=1;return a;}
    size_t index(int64_t sample) const noexcept{return static_cast<size_t>(sample)&mask;}
    double read(const std::vector<double>& buffer,int64_t sample) const noexcept {
        return sample<0?0:buffer[index(sample)];
    }
    double interpolate(const std::vector<double>& buffer,double sample) const noexcept {
        const auto centre=static_cast<int64_t>(std::floor(sample));const double f=sample-centre;
        const double a=read(buffer,centre-1),b=read(buffer,centre),c=read(buffer,centre+1),d=read(buffer,centre+2);
        return b+.5*f*(c-a+f*(2*a-5*b+4*c-d+f*(3*(b-c)+d-a)));
    }
    std::array<Channel,2> channels;
    std::vector<Decision> decisions;
    std::vector<double> highEvidence;
    PitchObserver observer;
    ControlTrajectory trajectory;
    Decision testDecision;
    bool testControlEnabled=false;
    double rate=48000,phase=.5,period=220,wet=0,low=0,highEnergy=0,totalEnergy=0;
    int latency=0,analysisDelay=0,synthesisDelay=0,envelopeLength=0;
    size_t mask=0,length=0;
    int64_t clock=0;
    uint64_t streamEpoch=0;
};
}
